"""
Tests for the shared disk render cache (services/render_cache.py) and its
integration in pdf_processor.
"""

import os
import time

import fitz
import pytest

from pdf_annotator.services import pdf_processor, render_cache


def _write_pdf(path, text: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 72), text, fontsize=24)
    doc.save(str(path))
    doc.close()


@pytest.fixture()
def counting_render(monkeypatch):
    """Count actual renders behind the cache."""
    calls = {"count": 0}
    original = pdf_processor._render_page

    def counted(file_path: str, page_num: int, dpi: int) -> bytes:
        calls["count"] += 1
        return original(file_path, page_num, dpi)

    monkeypatch.setattr(pdf_processor, "_render_page", counted)
    return calls


class TestDiskCache:
    def test_second_call_served_from_disk(
        self, app, tmp_path, sample_pdf, counting_render
    ):
        with app.app_context():
            first = pdf_processor.render_page_to_image(str(sample_pdf), 1, dpi=72)
            second = pdf_processor.render_page_to_image(str(sample_pdf), 1, dpi=72)

        assert first == second
        assert counting_render["count"] == 1

    def test_rewritten_pdf_renders_fresh_without_any_clear(
        self, app, tmp_path, counting_render
    ):
        """The multi-worker regression: after a PDF is replaced/OCRed, no
        worker may serve the old page image — with mtime/size keying that
        holds without any explicit cache clearing."""
        pdf_path = tmp_path / "mutating.pdf"
        _write_pdf(pdf_path, "Version Eins")

        with app.app_context():
            before = pdf_processor.render_page_to_image(str(pdf_path), 1, dpi=72)

            time.sleep(0.01)  # ensure a different mtime_ns
            _write_pdf(pdf_path, "Version Zwei — ganz anderer Inhalt")

            after = pdf_processor.render_page_to_image(str(pdf_path), 1, dpi=72)

        assert counting_render["count"] == 2
        assert before != after

    def test_different_dpi_cached_separately(self, app, sample_pdf, counting_render):
        with app.app_context():
            pdf_processor.render_page_to_image(str(sample_pdf), 1, dpi=72)
            pdf_processor.render_page_to_image(str(sample_pdf), 1, dpi=96)

        assert counting_render["count"] == 2

    def test_layout_round_trips_through_json_cache(self, app, sample_pdf):
        with app.app_context():
            first = pdf_processor.get_page_text_layout(str(sample_pdf), 1)
            second = pdf_processor.get_page_text_layout(str(sample_pdf), 1)

        assert first == second
        words = [w["text"] for line in first["lines"] for w in line["words"]]
        assert "Test" in words

    def test_invalid_page_error_is_not_cached(self, app, sample_pdf):
        with app.app_context():
            with pytest.raises(ValueError):
                pdf_processor.get_page_text_layout(str(sample_pdf), 99)
            # No poisoned cache entry: valid pages still work.
            layout = pdf_processor.get_page_text_layout(str(sample_pdf), 1)
        assert layout["lines"]

    def test_no_temp_files_left_behind(self, app, tmp_path, sample_pdf):
        cache_dir = app.config["RENDER_CACHE_FOLDER"]
        with app.app_context():
            pdf_processor.render_page_to_image(str(sample_pdf), 1, dpi=72)
            pdf_processor.get_page_text_layout(str(sample_pdf), 1)

        leftovers = [p for p in cache_dir.rglob("*") if ".tmp-" in p.name]
        assert leftovers == []

    def test_uncached_outside_app_context(self, sample_pdf, counting_render):
        assert pdf_processor.render_page_to_image(str(sample_pdf), 1, dpi=72)
        assert pdf_processor.render_page_to_image(str(sample_pdf), 1, dpi=72)
        assert counting_render["count"] == 2


class TestPrune:
    def _entry(self, cache_dir, name: str, size: int, age_seconds: int):
        path = cache_dir / name[:2] / name / "page1@72.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * size)
        stamp = time.time() - age_seconds
        os.utime(path, (stamp, stamp))
        return path

    def test_prunes_oldest_first_until_under_budget(self, tmp_path):
        cache_dir = tmp_path / "cache"
        old = self._entry(cache_dir, "aa11", 600, age_seconds=3600)
        new = self._entry(cache_dir, "bb22", 600, age_seconds=60)

        freed = render_cache.prune(cache_dir, max_bytes=1000)

        assert freed == 600
        assert not old.exists()
        assert new.exists()

    def test_no_prune_when_under_budget(self, tmp_path):
        cache_dir = tmp_path / "cache"
        entry = self._entry(cache_dir, "cc33", 100, age_seconds=3600)

        assert render_cache.prune(cache_dir, max_bytes=1000) == 0
        assert entry.exists()

    def test_removes_stale_temp_files_and_empty_dirs(self, tmp_path):
        cache_dir = tmp_path / "cache"
        entry = self._entry(cache_dir, "dd44", 600, age_seconds=3600)
        tmp_file = entry.with_name("page1@72.png.tmp-123-abc")
        tmp_file.write_bytes(b"partial")

        render_cache.prune(cache_dir, max_bytes=0)

        assert not tmp_file.exists()
        assert not entry.exists()
        assert not entry.parent.exists()  # emptied digest dir removed

    def test_missing_cache_dir_is_noop(self, tmp_path):
        assert render_cache.prune(tmp_path / "nichts", max_bytes=100) == 0
