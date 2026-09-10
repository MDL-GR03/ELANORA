"""Create a minimal accepted project used by the disposable recovery drill."""

import argparse
import asyncio
import hashlib
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.model.instance import Instance
from app.model.instance_asset import InstanceAsset
from app.model.project import Project
from app.model.user import User
from app.service.elan import ElanService
from app.service.git_operations import GitCommandRunner
from app.service.project_revision import append_project_revision


async def seed(database_url: str, projects_root: Path, assets_root: Path) -> None:
    """Persist one project whose disk and revision ledger are internally consistent."""
    engine = create_async_engine(database_url)
    session_maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        async with session_maker() as db:
            institution = Instance(
                instance_name="recovery-drill",
                institution_name="Recovery Drill Institute",
                contact_email="admin@recovery-drill.invalid",
                domain="recovery-drill.invalid",
                timezone="UTC",
            )
            administrator = User(
                username="recovery-admin",
                email="recovery-admin@recovery-drill.invalid",
                hashed_password="unused-recovery-drill-value",  # noqa: S106
                first_name="Recovery",
                last_name="Administrator",
                affiliation="Recovery Drill Institute",
                department="Operations",
                activation_code="fixture",
                instance=institution,
            )
            project = Project(
                project_name="recovery-corpus",
                project_path="recovery-corpus",
                description="Disposable disaster-recovery proof",
                instance=institution,
            )
            db.add_all([institution, administrator, project])
            await db.flush()

            project_path = projects_root / project.project_name
            elan_directory = project_path / "elan_files"
            elan_directory.mkdir(parents=True)
            fixture = (
                Path(__file__).parents[1]
                / "tests"
                / "fixtures"
                / "eaf"
                / "complete-valid.eaf"
            )
            eaf_path = elan_directory / "recovery-session.eaf"
            eaf_path.write_bytes(fixture.read_bytes())
            (project_path / "README.md").write_text(
                "Recovery drill\n", encoding="utf-8"
            )
            (project_path / ".gitignore").write_text("*.tmp\n", encoding="utf-8")
            runner = GitCommandRunner(project_path, maintain_backup=False)
            runner.run(["init", "--initial-branch=master"], check=True)
            runner.run(["config", "user.name", "ELANORA recovery drill"], check=True)
            runner.run(
                ["config", "user.email", "recovery-drill@elanora.invalid"],
                check=True,
            )
            runner.run(["add", "."], check=True)
            runner.run(["commit", "-m", "Recovery drill baseline"], check=True)

            await ElanService(db).process_single_file(
                str(eaf_path),
                administrator.user_id,
                project.project_name,
                commit_changes=False,
            )
            await append_project_revision(
                db,
                project_id=project.project_id,
                git_commit=runner.get_commit_hash(),
                parent_git_commit=None,
                source_type="migration",
                actor_user_id=administrator.user_id,
                details={"purpose": "automated recovery drill"},
            )
            logo = b"recovery-drill-logo"
            storage_key = "logos/recovery-drill.bin"
            asset_path = assets_root / storage_key
            asset_path.parent.mkdir(parents=True)
            asset_path.write_bytes(logo)
            db.add(
                InstanceAsset(
                    instance_id=institution.instance_id,
                    kind="logo",
                    storage_key=storage_key,
                    content_type="application/octet-stream",
                    byte_size=len(logo),
                    sha256=hashlib.sha256(logo).hexdigest(),
                    width=1,
                    height=1,
                    created_by=administrator.user_id,
                )
            )
            await db.commit()
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--projects", required=True, type=Path)
    parser.add_argument("--assets", required=True, type=Path)
    arguments = parser.parse_args()
    asyncio.run(seed(arguments.database_url, arguments.projects, arguments.assets))


if __name__ == "__main__":
    main()
