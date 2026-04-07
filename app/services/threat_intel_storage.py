from __future__ import annotations

import shutil
from pathlib import Path


class ThreatIntelLocalStorage:
    """Local filesystem helper for the phase-1 threat-intel workflow."""

    def __init__(self, base_dir: str | Path = "data/threat_intel/raw/pdfs"):
        self.base_dir = Path(base_dir)

    def ensure_base_dir(self) -> Path:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        return self.base_dir

    def list_local_pdfs(self) -> list[Path]:
        if not self.base_dir.exists():
            return []
        return sorted(
            path
            for path in self.base_dir.iterdir()
            if path.is_file() and path.suffix.lower() == ".pdf"
        )

    def resolve_pdf(self, filename: str) -> Path:
        requested = Path(filename)
        if requested.name != filename:
            raise FileNotFoundError(f"PDF file not found: {self.base_dir / filename}")

        base_dir = self.ensure_base_dir().resolve()
        path = (base_dir / requested.name).resolve()
        try:
            path.relative_to(base_dir)
        except ValueError as exc:
            raise FileNotFoundError(f"PDF file not found: {self.base_dir / filename}") from exc

        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"PDF file not found: {self.base_dir / filename}")
        return path

    def read_pdf_bytes(self, filename: str) -> bytes:
        return self.resolve_pdf(filename).read_bytes()

    def sync_from_directory(self, source_dir: str | Path, *, overwrite: bool = True) -> list[Path]:
        source_path = Path(source_dir)
        if not source_path.exists() or not source_path.is_dir():
            raise FileNotFoundError(f"Source directory not found: {source_path}")

        target_dir = self.ensure_base_dir()
        copied_paths: list[Path] = []
        for path in sorted(source_path.iterdir()):
            if not path.is_file() or path.suffix.lower() != ".pdf":
                continue
            target_path = target_dir / path.name
            if target_path.exists() and not overwrite:
                copied_paths.append(target_path)
                continue
            shutil.copy2(path, target_path)
            copied_paths.append(target_path)
        return copied_paths
