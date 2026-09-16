"""Shared PostgreSQL fixtures for database integration tests."""

import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Register every table, so truncation never depends on what a test imported.
import app.model  # noqa: F401
from app.db.database import Base

DEFAULT_TEST_DATABASE_URL = (
    "postgresql+asyncpg://elanora_test:elanora-test-only@127.0.0.1:5418/elanora_test"
)


def _database_url() -> str:
    database_url = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
    if not database_url.startswith("postgresql+asyncpg://"):
        raise RuntimeError("Integration tests require PostgreSQL through asyncpg")
    return database_url


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """Provide a clean session backed by the migrated PostgreSQL test database."""
    engine = create_async_engine(_database_url(), pool_pre_ping=True)
    table_names = ", ".join(
        f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables)
    )
    async with engine.begin() as connection:
        await connection.execute(
            text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")
        )

    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(
    session: AsyncSession,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Open independent sessions on separate connections for contention tests.

    Depends on ``session`` so the database is truncated before any worker
    connects. Each session from this factory is its own PostgreSQL backend, so
    row locks taken in one genuinely block another.
    """
    engine = create_async_engine(
        _database_url(), pool_pre_ping=True, pool_size=10, max_overflow=5
    )
    try:
        yield async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def api_client(
    session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    """Drive the real application, middleware included, over HTTP.

    Every request gets its own database session, as in production, so commits
    and rollbacks behave as they do behind a browser. Project storage and
    recovery copies live under a temporary directory. Cookies follow their
    paths, just as a browser would send them.
    """
    from app.api.v1 import git_shared  # noqa: PLC0415 - imports the whole app
    from app.core.limiter import limiter  # noqa: PLC0415
    from app.db.database import get_db  # noqa: PLC0415
    from app.main import app  # noqa: PLC0415
    from app.service.contribution_change_set import (  # noqa: PLC0415
        ContributionChangeSetCoordinator,
    )
    from app.service.git import GitService  # noqa: PLC0415
    from app.service.project_sync import ProjectSyncCoordinator  # noqa: PLC0415
    from app.utils import file_processing, project_backup  # noqa: PLC0415

    projects_root = tmp_path / "projects"
    monkeypatch.setattr(file_processing, "ELAN_PROJECTS_BASE_PATH", str(projects_root))
    monkeypatch.setattr(
        project_backup, "ELAN_BACKUPS_BASE_PATH", str(tmp_path / "recovery")
    )
    git_service = GitService(base_path=str(projects_root))
    monkeypatch.setattr(git_shared, "git_service", git_service)
    monkeypatch.setattr(
        git_shared,
        "contribution_change_sets",
        ContributionChangeSetCoordinator(git_service),
    )
    monkeypatch.setattr(
        git_shared, "sync_coordinator", ProjectSyncCoordinator(git_service)
    )

    engine = create_async_engine(_database_url(), pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    async def request_session() -> AsyncIterator[AsyncSession]:
        async with factory() as request_db:
            try:
                yield request_db
            except BaseException:
                await request_db.rollback()
                raise

    app.dependency_overrides[get_db] = request_session
    limiter.reset()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()


ACCOUNT_PASSWORD = "Correct-horse-battery-7"  # noqa: S105 - test-only credential


@dataclass(frozen=True)
class InstitutionAccounts:
    """Verified accounts in one institution, all using ``ACCOUNT_PASSWORD``."""

    instance_id: int
    admin_id: int
    admin_login: str
    researcher_id: int
    researcher_login: str
    outsider_id: int
    outsider_login: str


@pytest_asyncio.fixture
async def institution_accounts(session: AsyncSession) -> InstitutionAccounts:
    """An administrator, a researcher and a researcher outside every project."""
    from app.model.enums import UserRole  # noqa: PLC0415
    from app.model.instance import Instance  # noqa: PLC0415
    from app.model.user import User  # noqa: PLC0415
    from app.utils.password_hashing import hash_password  # noqa: PLC0415

    instance = Instance(
        instance_name="HTTP Lab",
        institution_name="HTTP Institute",
        contact_email="admin@http.example",
        domain="http.example",
        timezone="UTC",
    )
    hashed = hash_password(ACCOUNT_PASSWORD)
    users = {
        name: User(
            username=name,
            email=f"{name}@http.example",
            hashed_password=hashed,
            first_name=name.title(),
            last_name="Tester",
            affiliation="HTTP Institute",
            department="Linguistics",
            activation_code="fixture",
            is_verified_account=True,
            role=UserRole.ADMIN if name == "admin" else UserRole.PUBLIC,
            instance=instance,
        )
        for name in ("admin", "researcher", "outsider")
    }
    session.add_all([instance, *users.values()])
    await session.commit()
    return InstitutionAccounts(
        instance_id=instance.instance_id,
        admin_id=users["admin"].user_id,
        admin_login="admin",
        researcher_id=users["researcher"].user_id,
        researcher_login="researcher",
        outsider_id=users["outsider"].user_id,
        outsider_login="outsider",
    )


GIT = "/api/v1/git"
PROJECT = "http-corpus"


class Browser:
    """One signed-in browser tab: cookies plus the CSRF header it echoes."""

    def __init__(self, client: AsyncClient) -> None:
        self.client = client
        self.csrf = ""

    async def sign_in(self, login: str) -> None:
        self.client.cookies.clear()
        response = await self.client.post(
            "/api/v1/auth/login", json={"login": login, "password": ACCOUNT_PASSWORD}
        )
        assert response.status_code == 200, response.text
        self.csrf = response.json()["csrf_token"]

    async def get(self, url: str):
        return await self.client.get(url)

    async def post(self, url: str, **kwargs):
        return await self.client.post(
            url, headers={"X-CSRF-Token": self.csrf}, **kwargs
        )

    async def put(self, url: str, **kwargs):
        return await self.client.put(url, headers={"X-CSRF-Token": self.csrf}, **kwargs)

    async def upload(
        self,
        project_id: int,
        filename: str,
        content: bytes,
        **fields: str,
    ):
        return await self.post(
            f"{GIT}/projects/{project_id}/upload",
            data={
                "user_name": "researcher",
                "contribution_summary": "Session one annotations",
                **fields,
            },
            files=[("files", (filename, content, "application/xml"))],
        )


async def project_with_member(browser: Browser, accounts: InstitutionAccounts) -> int:
    await browser.sign_in(accounts.admin_login)
    created = await browser.post(
        f"{GIT}/projects/create",
        json={"project_name": PROJECT, "description": "HTTP workflow"},
    )
    assert created.status_code == 200, created.text
    listed = await browser.get(f"{GIT}/projects")
    (project,) = listed.json()["projects"]
    added = await browser.post(
        f"/api/v1/project-associations/projects/{project['project_id']}/users",
        json={"user_id": accounts.researcher_id, "permission": "write"},
    )
    assert added.status_code == 200, added.text
    return project["project_id"]
