"""The cross-process lock that serializes writes to one project's Git tree.

API requests and the publication worker are separate processes that both
mutate a project's working tree, so they coordinate through a file lock rather
than a database transaction.
"""

import asyncio
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from app.core.errors import ElanoraError
from app.dependency import project_lock
from app.dependency.project_lock import acquire_project_write_lock
from app.service.git import GitService
from app.utils.file_processing import get_elanora_projects_base_path


async def _occupy(
    project_id: int, root: Path, label: str, timeline: list[str], hold: float
) -> None:
    async with acquire_project_write_lock(project_id, root):
        timeline.append(f"enter {label}")
        await asyncio.sleep(hold)
        timeline.append(f"exit {label}")


@pytest.mark.asyncio
async def test_writers_to_the_same_project_never_overlap(tmp_path: Path) -> None:
    timeline: list[str] = []

    await asyncio.gather(
        _occupy(7, tmp_path, "a", timeline, 0.15),
        _occupy(7, tmp_path, "b", timeline, 0.15),
        _occupy(7, tmp_path, "c", timeline, 0.15),
    )

    # Every entry is immediately followed by its own exit: no interleaving.
    assert len(timeline) == 6
    for enter, exit_ in zip(timeline[::2], timeline[1::2], strict=True):
        assert enter.startswith("enter ")
        assert exit_ == f"exit {enter.removeprefix('enter ')}"


@pytest.mark.asyncio
async def test_writers_to_different_projects_run_in_parallel(tmp_path: Path) -> None:
    """Serializing unrelated projects would stall the whole installation."""
    timeline: list[str] = []

    await asyncio.gather(
        _occupy(7, tmp_path, "seven", timeline, 0.2),
        _occupy(8, tmp_path, "eight", timeline, 0.2),
    )

    first_exit = next(i for i, event in enumerate(timeline) if event.startswith("exit"))
    assert first_exit == 2, timeline


@pytest.mark.asyncio
async def test_a_writer_that_cannot_get_the_lock_is_told_the_project_is_busy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(project_lock, "LOCK_TIMEOUT_SECONDS", 0.2)
    holding = asyncio.Event()
    release = asyncio.Event()

    async def holder() -> None:
        async with acquire_project_write_lock(7, tmp_path):
            holding.set()
            await release.wait()

    task = asyncio.create_task(holder())
    await holding.wait()
    try:
        with pytest.raises(ElanoraError) as refused:
            async with acquire_project_write_lock(7, tmp_path):
                pass
        assert refused.value.status_code == 423
    finally:
        release.set()
        await task


@pytest.mark.asyncio
async def test_a_release_on_a_different_thread_really_frees_the_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: a cross-thread release used to leak the lock until restart.

    Acquire and release each go through asyncio.to_thread, and the executor may
    run them on different threads. FileLock is thread-local by default, so such
    a release did nothing and every later write to the project timed out with
    a 423. The test forces the two calls onto different threads rather than
    relying on how the executor happens to schedule them.
    """
    # Thread objects, not idents: an ident is reused once its thread exits.
    threads_used: list[threading.Thread] = []

    async def on_a_fresh_thread(
        func: Callable[..., Any], /, *args: Any, **kwargs: Any
    ) -> Any:
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()

        def run() -> None:
            threads_used.append(threading.current_thread())
            try:
                result = func(*args, **kwargs)
            except BaseException as error:
                loop.call_soon_threadsafe(future.set_exception, error)
            else:
                loop.call_soon_threadsafe(future.set_result, result)

        threading.Thread(target=run, daemon=True).start()
        return await future

    monkeypatch.setattr(project_lock.asyncio, "to_thread", on_a_fresh_thread)
    monkeypatch.setattr(project_lock, "LOCK_TIMEOUT_SECONDS", 0.5)

    async with acquire_project_write_lock(7, tmp_path):
        pass

    assert len(threads_used) == 2
    assert threads_used[0] is not threads_used[1], "acquire and release shared a thread"

    # If the release had been a no-op, this would time out with a 423.
    async with acquire_project_write_lock(7, tmp_path):
        pass


def test_api_requests_and_the_publication_worker_share_one_lock_root() -> None:
    """Two lock directories would mean the two processes never exclude each other.

    The API derives its root from get_elanora_projects_base_path() and the worker
    from GitService().base_path. They are computed independently and must agree.
    """
    api_root = Path(get_elanora_projects_base_path()).resolve()
    worker_root = GitService().base_path.resolve()

    assert api_root == worker_root
