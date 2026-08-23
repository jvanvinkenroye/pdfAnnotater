"""
Disk-based cache for rendered page images and text layouts.

Entries are keyed by the PDF's content identity (resolved path + mtime_ns
+ size). Every mutation in this app (replace, append, OCR, delete page)
rewrites the PDF file, so the key changes and all workers automatically
stop hitting stale entries — no cross-process invalidation signal needed,
unlike the per-process lru_cache this replaces. Old entries are reclaimed
by prune() (run by the cleanup thread), not by explicit invalidation.
"""

import hashlib
import json
import os
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pdf_annotator.utils.logger import get_logger

logger = get_logger(__name__)


def _doc_dir(cache_dir: Path, file_path: Path) -> Path:
    stat = file_path.stat()
    raw = f"{file_path.resolve()}|{stat.st_mtime_ns}|{stat.st_size}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return cache_dir / digest[:2] / digest


def _atomic_write(target: Path, data: bytes) -> None:
    # Unique temp name per writer: concurrent workers may render the same
    # page twice (harmless) but never serve a torn file.
    tmp = target.with_name(f"{target.name}.tmp-{os.getpid()}-{uuid.uuid4().hex[:8]}")
    tmp.write_bytes(data)
    os.replace(tmp, target)


def _get_or_create(target: Path, produce: Callable[[], bytes]) -> bytes:
    try:
        data = target.read_bytes()
        # Refresh mtime so prune() evicts least-recently-used entries.
        os.utime(target)
        return data
    except FileNotFoundError:
        pass
    data = produce()
    target.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(target, data)
    return data


def get_or_render_page(
    cache_dir: Path,
    file_path: Path,
    page_num: int,
    dpi: int,
    render: Callable[[], bytes],
) -> bytes:
    """Return the cached PNG for a page, rendering and storing on miss."""
    target = _doc_dir(cache_dir, file_path) / f"page{page_num}@{dpi}.png"
    return _get_or_create(target, render)


def get_or_load_layout(
    cache_dir: Path,
    file_path: Path,
    page_num: int,
    extract: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    """Return the cached text layout for a page, extracting on miss."""
    target = _doc_dir(cache_dir, file_path) / f"page{page_num}.layout.json"

    def produce() -> bytes:
        return json.dumps(extract()).encode("utf-8")

    return dict(json.loads(_get_or_create(target, produce).decode("utf-8")))


def prune(cache_dir: Path, max_bytes: int) -> int:
    """
    Delete least-recently-used cache entries until the cache fits max_bytes.

    Also removes leftover temp files and empty directories. Returns the
    number of bytes freed. Safe to run concurrently with readers/writers —
    a pruned entry is simply re-rendered on the next request.
    """
    if not cache_dir.is_dir():
        return 0

    entries: list[tuple[float, int, Path]] = []
    total = 0
    for path in cache_dir.rglob("*"):
        if not path.is_file():
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        if ".tmp-" in path.name:
            path.unlink(missing_ok=True)
            continue
        entries.append((stat.st_mtime, stat.st_size, path))
        total += stat.st_size

    freed = 0
    if total > max_bytes:
        entries.sort()  # oldest first
        for _mtime, size, path in entries:
            if total - freed <= max_bytes:
                break
            path.unlink(missing_ok=True)
            freed += size
        logger.info("Render cache pruned: %d bytes freed", freed)

    # Drop directories emptied by pruning (deepest first).
    for directory in sorted(
        (p for p in cache_dir.rglob("*") if p.is_dir()), reverse=True
    ):
        try:
            directory.rmdir()
        except OSError:
            pass

    return freed
