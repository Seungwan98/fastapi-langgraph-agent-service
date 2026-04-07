import argparse
import os
from pathlib import Path

from app.services.retriever import build_rag_index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a JSON RAG index from local documents.")
    parser.add_argument("--input-dir", default="docs/knowledge", help="Directory containing markdown/text knowledge files")
    parser.add_argument("--output", default="data/rag_index.json", help="Output JSON index path")
    parser.add_argument("--embedding-model", default="text-embedding-3-small", help="OpenAI embedding model")
    parser.add_argument("--chunk-size", type=int, default=800, help="Characters per chunk")
    parser.add_argument("--chunk-overlap", type=int, default=120, help="Overlapping characters between chunks")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        result = build_rag_index(
            input_dir=Path(args.input_dir),
            output_path=Path(args.output),
            embedding_model=args.embedding_model,
            api_key=os.getenv("OPENAI_API_KEY", ""),
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    print(f"Wrote {result.chunk_count} chunks from {result.document_count} documents to {result.output_path}")


if __name__ == "__main__":
    main()
