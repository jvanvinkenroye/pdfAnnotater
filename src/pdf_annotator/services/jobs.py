"""
In-process background jobs for long-running work (OCR, PDF export).

One worker thread per process runs jobs off the request path; status
lives in the shared SQLite jobs table and artifacts on the shared
filesystem, so with multiple Gunicorn workers any worker can answer a
poll for a job that another worker is running. No broker or external
queue is needed, and the same code path serves the single-process
desktop app.
"""

import json
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from pdf_annotator.models.database import DatabaseManager
from pdf_annotator.utils.logger import get_logger

logger = get_logger(__name__)

# A job stuck in pending/running longer than this is considered orphaned
# (killed worker, hung subprocess) and flipped to error by the cleanup
# pass. Must exceed OCR_TIMEOUT_SECONDS with margin.
JOB_STALE_SECONDS = 900

# Terminal job rows (and their artifacts) are removed after this age.
FINISHED_JOB_RETENTION_SECONDS = 24 * 3600

# The runner returns a result dict; the "result_path" key is persisted to
# the jobs.result_path column, the rest to result_json.
Runner = Callable[[], dict[str, Any] | None]

_executor: ThreadPoolExecutor | None = None
_executor_lock = threading.Lock()


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    with _executor_lock:
        if _executor is None:
            # One job at a time per process: OCR and 300-DPI export are
            # CPU-heavy (ocrmypdf spawns its own process pool); requests
            # keep being served on the other threads.
            _executor = ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="pdf-annotator-job"
            )
        return _executor


def submit_job(
    db: DatabaseManager,
    job_type: str,
    doc_id: str,
    user_id: str,
    runner: Runner,
) -> str:
    """
    Insert a job row and execute `runner` on the background thread.

    The runner must not touch current_app/request/current_user — capture
    everything it needs (the db instance, file paths, config values) in
    the closure at submit time.
    """
    job_id = db.create_job(job_type, doc_id, user_id)
    _get_executor().submit(_run_job, db, job_id, runner)
    logger.info("Submitted %s job %s for document %s", job_type, job_id, doc_id)
    return job_id


def _run_job(db: DatabaseManager, job_id: str, runner: Runner) -> None:
    db.mark_job_running(job_id)
    try:
        result = runner() or {}
    except Exception as e:
        logger.error("Background job %s failed: %s", job_id, e, exc_info=True)
        db.finish_job(job_id, "error", error=str(e))
        return

    result_path = result.pop("result_path", None)
    db.finish_job(
        job_id,
        "done",
        result_path=result_path,
        result_json=json.dumps(result) if result else None,
    )
    logger.info("Background job %s finished", job_id)
