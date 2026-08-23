"""
Tests for the background job service and job-related endpoints.
"""

import time
import uuid

from pdf_annotator.services import jobs
from pdf_annotator.services.jobs import submit_job


class TestJobLifecycle:
    def test_successful_job_stores_result(self, app, db, uploaded_pdf, inline_jobs):
        with app.app_context():
            job_id = submit_job(
                db,
                "export_pdf",
                uploaded_pdf,
                db.test_user_id,
                lambda: {"result_path": "/tmp/x.pdf", "filename": "x.pdf"},
            )

        job = db.get_job(job_id)
        assert job["status"] == "done"
        assert job["result_path"] == "/tmp/x.pdf"
        assert "x.pdf" in job["result_json"]
        assert job["started_at"] is not None
        assert job["finished_at"] is not None

    def test_failing_job_stores_error(self, app, db, uploaded_pdf, inline_jobs):
        def boom() -> dict:
            raise RuntimeError("kaputt")

        with app.app_context():
            job_id = submit_job(db, "ocr", uploaded_pdf, db.test_user_id, boom)

        job = db.get_job(job_id)
        assert job["status"] == "error"
        assert job["error"] == "kaputt"

    def test_real_thread_executes_job(self, app, db, uploaded_pdf):
        """Smoke test through the actual ThreadPoolExecutor."""
        with app.app_context():
            job_id = submit_job(db, "ocr", uploaded_pdf, db.test_user_id, lambda: {})

        deadline = time.time() + 10
        while time.time() < deadline:
            job = db.get_job(job_id)
            if job["status"] in ("done", "error"):
                break
            time.sleep(0.05)

        assert job["status"] == "done"


class TestJobStatusEndpoint:
    def test_unknown_job_404(self, logged_in_client):
        response = logged_in_client.get(f"/viewer/api/jobs/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_foreign_job_403(self, client, db, uploaded_pdf, second_user):
        job_id = db.create_job("ocr", uploaded_pdf, db.test_user_id)

        login = client.post(
            "/auth/login",
            data={"username": "seconduser", "password": "secondpassword"},
        )
        assert login.status_code == 302

        response = client.get(f"/viewer/api/jobs/{job_id}")
        assert response.status_code == 403

    def test_pending_job_status(self, logged_in_client, db, uploaded_pdf, user):
        job_id = db.create_job("ocr", uploaded_pdf, user)

        response = logged_in_client.get(f"/viewer/api/jobs/{job_id}")
        assert response.status_code == 200
        assert response.get_json()["status"] == "pending"


class TestOcrJobGuards:
    def test_duplicate_active_ocr_job_409(
        self, app, logged_in_client, db, uploaded_pdf, user, monkeypatch
    ):
        monkeypatch.setattr("pdf_annotator.services.ocr.ocr_available", lambda: True)
        db.create_job("ocr", uploaded_pdf, user)  # stays pending

        response = logged_in_client.post(f"/viewer/api/ocr/{uploaded_pdf}")
        assert response.status_code == 409
        assert "läuft bereits" in response.get_json()["error"]


class TestDownloadEndpoint:
    def test_download_pending_job_409(self, logged_in_client, db, uploaded_pdf, user):
        job_id = db.create_job("export_pdf", uploaded_pdf, user)

        response = logged_in_client.get(f"/export/download/{job_id}")
        assert response.status_code == 409

    def test_download_vanished_artifact_404(
        self, logged_in_client, db, uploaded_pdf, user
    ):
        job_id = db.create_job("export_pdf", uploaded_pdf, user)
        db.finish_job(job_id, "done", result_path="/nirgendwo/weg.pdf")

        response = logged_in_client.get(f"/export/download/{job_id}")
        assert response.status_code == 404


class TestJobMaintenance:
    def _age_job(self, db, job_id: str, seconds: int) -> None:
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE jobs SET created_at = datetime('now', ?),"
                " finished_at = datetime('now', ?) WHERE id = ?",
                (f"-{seconds} seconds", f"-{seconds} seconds", job_id),
            )

    def test_stale_running_job_flipped_to_error(self, db, uploaded_pdf, user):
        job_id = db.create_job("ocr", uploaded_pdf, user)
        db.mark_job_running(job_id)
        self._age_job(db, job_id, jobs.JOB_STALE_SECONDS + 60)

        flipped = db.mark_stale_jobs_failed(jobs.JOB_STALE_SECONDS)

        assert flipped == 1
        job = db.get_job(job_id)
        assert job["status"] == "error"
        assert "abgebrochen" in job["error"]

    def test_fresh_running_job_untouched(self, db, uploaded_pdf, user):
        job_id = db.create_job("ocr", uploaded_pdf, user)
        db.mark_job_running(job_id)

        assert db.mark_stale_jobs_failed(jobs.JOB_STALE_SECONDS) == 0
        assert db.get_job(job_id)["status"] == "running"

    def test_delete_finished_jobs_returns_artifact_paths(self, db, uploaded_pdf, user):
        old_id = db.create_job("export_pdf", uploaded_pdf, user)
        db.finish_job(old_id, "done", result_path="/tmp/alt.pdf")
        self._age_job(db, old_id, 48 * 3600)

        new_id = db.create_job("export_pdf", uploaded_pdf, user)
        db.finish_job(new_id, "done", result_path="/tmp/neu.pdf")

        paths = db.delete_finished_jobs(24 * 3600)

        assert paths == ["/tmp/alt.pdf"]
        assert db.get_job(old_id) is None
        assert db.get_job(new_id) is not None
