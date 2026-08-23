"""
Periodic maintenance, moved off the request path.

One daemon thread per process wakes every CLEANUP_INTERVAL_SECONDS and:
- deletes export artifacts older than EXPORT_MAX_AGE_SECONDS
- flips orphaned background jobs to 'error' (killed worker, hung tool)
- expires finished job rows and unlinks their artifacts
- prunes the render cache to its size budget

Every task is idempotent, so correctness never depends on exclusion;
with multiple Gunicorn workers a non-blocking file lock merely skips
redundant rounds. The same mechanism works unchanged in the
single-process desktop app.
"""

import random
import threading
import time
from pathlib import Path
from typing import IO, TYPE_CHECKING

from pdf_annotator.models.database import DatabaseManager
from pdf_annotator.services import render_cache
from pdf_annotator.services.jobs import (
    FINISHED_JOB_RETENTION_SECONDS,
    JOB_STALE_SECONDS,
)
from pdf_annotator.utils.logger import get_logger

if TYPE_CHECKING:
    from flask import Flask

logger = get_logger(__name__)

CLEANUP_INTERVAL_SECONDS = 15 * 60
JITTER_SECONDS = 60
STARTUP_DELAY_SECONDS = 10

# Max age for export files before cleanup (1 hour)
EXPORT_MAX_AGE_SECONDS = 3600


def cleanup_old_exports(
    export_folder: Path, max_age_seconds: int = EXPORT_MAX_AGE_SECONDS
) -> None:
    """Remove export files older than max_age_seconds."""
    try:
        if not export_folder.exists():
            return

        now = time.time()
        for file_path in export_folder.iterdir():
            if file_path.is_file():
                age = now - file_path.stat().st_mtime
                if age > max_age_seconds:
                    file_path.unlink(missing_ok=True)
                    logger.debug("Cleaned up old export: %s", file_path.name)
    except Exception as e:
        logger.warning(f"Export cleanup failed: {e}")


def run_cleanup_once(
    db: DatabaseManager,
    export_folder: Path,
    cache_folder: Path,
    cache_max_bytes: int,
) -> None:
    """Run one maintenance round. Each task is independently idempotent."""
    cleanup_old_exports(export_folder)

    stale = db.mark_stale_jobs_failed(JOB_STALE_SECONDS)
    if stale:
        logger.info("Marked %d orphaned background jobs as failed", stale)

    for path_str in db.delete_finished_jobs(FINISHED_JOB_RETENTION_SECONDS):
        Path(path_str).unlink(missing_ok=True)

    render_cache.prune(cache_folder, cache_max_bytes)


def _try_lock(lock_path: Path) -> IO[str] | None:
    """
    Take a non-blocking exclusive flock; None when another process holds it.

    On platforms without fcntl (Windows dev) the lock is skipped — every
    task is idempotent, the lock only avoids duplicate work.
    """
    try:
        import fcntl
    except ImportError:
        return open(lock_path, "w")  # noqa: SIM115 - held for the round

    handle = open(lock_path, "w")  # noqa: SIM115 - held for the round
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def start_cleanup_thread(app: "Flask") -> threading.Thread:
    """
    Start the per-process cleanup daemon thread for this app.

    The first round runs shortly after startup so jobs orphaned by a
    previous crash/deploy are recovered promptly.
    """
    export_folder = Path(app.config["EXPORT_FOLDER"])
    cache_folder = Path(app.config["RENDER_CACHE_FOLDER"])
    cache_max_bytes = int(app.config["RENDER_CACHE_MAX_BYTES"])
    db: DatabaseManager = app.extensions["db"]
    lock_path = export_folder.parent / "cleanup.lock"
    stop = threading.Event()

    def loop() -> None:
        stop.wait(STARTUP_DELAY_SECONDS)
        while not stop.is_set():
            lock = _try_lock(lock_path)
            if lock is not None:
                try:
                    run_cleanup_once(db, export_folder, cache_folder, cache_max_bytes)
                except Exception as e:
                    logger.warning("Cleanup round failed: %s", e, exc_info=True)
                finally:
                    lock.close()
            stop.wait(CLEANUP_INTERVAL_SECONDS + random.uniform(0, JITTER_SECONDS))

    thread = threading.Thread(target=loop, name="pdf-annotator-cleanup", daemon=True)
    thread.start()
    app.extensions["cleanup_stop"] = stop
    return thread
