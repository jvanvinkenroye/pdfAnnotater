"""
Tests for the periodic cleanup service.
"""

import os
import time

from pdf_annotator.services import cleanup, jobs


def _aged_file(folder, name: str, age_seconds: int):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(b"inhalt")
    stamp = time.time() - age_seconds
    os.utime(path, (stamp, stamp))
    return path


class TestRunCleanupOnce:
    def test_old_exports_deleted_fresh_kept(self, db, tmp_path):
        exports = tmp_path / "exports"
        old = _aged_file(exports, "alt.pdf", cleanup.EXPORT_MAX_AGE_SECONDS + 60)
        fresh = _aged_file(exports, "neu.pdf", 10)

        cleanup.run_cleanup_once(db, exports, tmp_path / "cache", 10**9)

        assert not old.exists()
        assert fresh.exists()

    def test_stale_job_flipped_and_expired_artifact_removed(
        self, db, tmp_path, uploaded_pdf, user
    ):
        # A running job orphaned long ago...
        stale_id = db.create_job("ocr", uploaded_pdf, user)
        db.mark_job_running(stale_id)
        # ...and an old finished export job with an artifact on disk.
        artifact = _aged_file(tmp_path / "exports", "fertig.pdf", 10)
        done_id = db.create_job("export_pdf", uploaded_pdf, user)
        db.finish_job(done_id, "done", result_path=str(artifact))
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE jobs SET created_at = datetime('now', '-2 days'),"
                " finished_at = datetime('now', '-2 days')"
            )

        cleanup.run_cleanup_once(db, tmp_path / "exports", tmp_path / "cache", 10**9)

        assert db.get_job(stale_id)["status"] == "error"
        assert db.get_job(done_id) is None
        assert not artifact.exists()

    def test_cache_pruned_to_budget(self, db, tmp_path):
        cache = tmp_path / "cache"
        entry = _aged_file(cache / "aa" / "aabb", "page1@72.png", 3600)

        cleanup.run_cleanup_once(db, tmp_path / "exports", cache, 0)

        assert not entry.exists()


class TestCleanupThread:
    def test_not_started_in_testing_config(self, app):
        assert "cleanup_stop" not in app.extensions

    def test_thread_runs_and_stops(self, app, tmp_path, monkeypatch):
        monkeypatch.setattr(cleanup, "STARTUP_DELAY_SECONDS", 0)
        monkeypatch.setattr(cleanup, "CLEANUP_INTERVAL_SECONDS", 0.05)
        monkeypatch.setattr(cleanup, "JITTER_SECONDS", 0)

        exports = tmp_path / "exports"
        old = _aged_file(exports, "alt.pdf", cleanup.EXPORT_MAX_AGE_SECONDS + 60)
        app.config["EXPORT_FOLDER"] = exports

        thread = cleanup.start_cleanup_thread(app)
        try:
            deadline = time.time() + 5
            while old.exists() and time.time() < deadline:
                time.sleep(0.02)
            assert not old.exists()
        finally:
            app.extensions["cleanup_stop"].set()
            thread.join(timeout=5)
            assert not thread.is_alive()

    def test_lock_is_exclusive(self, tmp_path):
        lock_path = tmp_path / "cleanup.lock"
        first = cleanup._try_lock(lock_path)
        assert first is not None

        second = cleanup._try_lock(lock_path)
        assert second is None

        first.close()
        third = cleanup._try_lock(lock_path)
        assert third is not None
        third.close()


class TestStaleConstants:
    def test_stale_threshold_exceeds_ocr_timeout(self):
        from pdf_annotator.services.ocr import OCR_TIMEOUT_SECONDS

        assert jobs.JOB_STALE_SECONDS > OCR_TIMEOUT_SECONDS
