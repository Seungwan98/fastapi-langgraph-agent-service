from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.threat_intel_rag import ThreatIntelRAGService
from app.services.threat_intel_storage import ThreatIntelLocalStorage


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest local threat-intel PDFs into parsed artifacts")
    parser.add_argument("--pdf-dir", default="data/threat_intel/raw/pdfs", help="Directory containing synced PDFs")
    parser.add_argument("--parsed-dir", default="data/threat_intel/parsed", help="Directory to store parsed artifacts")
    parser.add_argument("--index-dir", default="data/threat_intel/index", help="Directory where the ingest step writes the reusable vector index")
    args = parser.parse_args()

    storage = ThreatIntelLocalStorage(base_dir=args.pdf_dir)
    pdfs = storage.list_local_pdfs()
    if not pdfs:
        raise SystemExit(f"No PDFs found in {storage.base_dir}. Run the sync script first.")

    service = ThreatIntelRAGService(parsed_dir=args.parsed_dir, index_dir=args.index_dir)
    results = service.ingest_directory(args.pdf_dir)

    print(f"Ingested {len(results)} PDF files into parsed artifacts")
    for result in results:
        print(
            f"- {result.doc_key}: pages={result.page_count} elements={result.element_count} "
            f"visuals={result.visual_summary_count} parents={result.parent_count}"
        )


if __name__ == "__main__":
    main()

