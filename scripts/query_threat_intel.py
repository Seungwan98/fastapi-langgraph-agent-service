from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.threat_intel_rag import ThreatIntelRAGService


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask a question over parsed threat-intel PDF artifacts")
    parser.add_argument("--question", required=True, help="Question to ask")
    parser.add_argument("--parsed-dir", default="data/threat_intel/parsed", help="Parsed artifact directory")
    parser.add_argument("--index-dir", default="data/threat_intel/index", help="Index artifact directory")
    args = parser.parse_args()

    service = ThreatIntelRAGService(parsed_dir=args.parsed_dir, index_dir=args.index_dir)
    result = service.query(args.question)

    print("=== ANSWER ===")
    print(result["answer"])
    print("\n=== SOURCES ===")
    for index, doc in enumerate(result["retrieved_docs"], start=1):
        print(f"[{index}] {doc.metadata}")


if __name__ == "__main__":
    main()
