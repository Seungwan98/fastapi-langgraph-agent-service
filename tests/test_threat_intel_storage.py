from __future__ import annotations

from pathlib import Path

import pytest

from app.services.threat_intel_storage import ThreatIntelLocalStorage


def test_sync_from_directory_copies_only_pdfs(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "a.pdf").write_bytes(b"pdf-a")
    (source / "b.PDF").write_bytes(b"pdf-b")
    (source / "note.txt").write_text("ignore", encoding="utf-8")

    storage = ThreatIntelLocalStorage(base_dir=tmp_path / "target")
    copied = storage.sync_from_directory(source)

    assert [path.name for path in copied] == ["a.pdf", "b.PDF"]
    assert [path.name for path in storage.list_local_pdfs()] == ["a.pdf", "b.PDF"]


def test_sync_from_directory_rejects_missing_source(tmp_path: Path):
    storage = ThreatIntelLocalStorage(base_dir=tmp_path / "target")

    with pytest.raises(FileNotFoundError):
        storage.sync_from_directory(tmp_path / "missing")


def test_read_pdf_bytes_raises_for_missing_file(tmp_path: Path):
    storage = ThreatIntelLocalStorage(base_dir=tmp_path / "target")
    storage.ensure_base_dir()

    with pytest.raises(FileNotFoundError):
        storage.read_pdf_bytes("missing.pdf")
