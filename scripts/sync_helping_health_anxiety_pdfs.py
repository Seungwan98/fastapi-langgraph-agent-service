from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.threat_intel_storage import ThreatIntelLocalStorage


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync local health-anxiety PDFs into the repo working directory")
    parser.add_argument(
        "--source",
        default="/Users/seungwan/Downloads/Helping Health Anxiety",
        help="Directory containing source PDFs",
    )
    parser.add_argument(
        "--target",
        default="data/threat_intel/raw/pdfs",
        help="Repo-local target directory",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Do not overwrite existing target files",
    )
    args = parser.parse_args()

    storage = ThreatIntelLocalStorage(base_dir=args.target)
    copied = storage.sync_from_directory(args.source, overwrite=not args.no_overwrite)

    print(f"Synced {len(copied)} PDF files into {storage.base_dir}")
    for path in copied:
        print(f"- {path}")


if __name__ == "__main__":
    main()
