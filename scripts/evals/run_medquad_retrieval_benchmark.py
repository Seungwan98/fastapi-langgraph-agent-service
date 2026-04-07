from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from scripts.evals.common import (
    ROOT as COMMON_ROOT,
    compute_retrieval_metrics,
    lexical_overlap_score,
    read_jsonl,
    write_json,
)


DEFAULT_DIR = COMMON_ROOT / "data" / "derived" / "eval_inputs"


def rank_corpus(query_text: str, corpus: list[dict]) -> list[tuple[str, float]]:
    """질의와의 어휘 겹침으로 문서 순위를 매긴다."""
    scored = []
    for row in corpus:
        doc_id = row.get("doc_id")
        text = row.get("text", "")
        scored.append((doc_id, lexical_overlap_score(query_text, text)))
    scored.sort(key=lambda item: (-item[1], item[0]))
    return scored


def run(corpus_path: Path, queries_path: Path, qrels_path: Path, output_path: Path, top_k: int = 20) -> dict:
    """MedQuAD 벤치마크 입력으로 검색 성능을 평가한다."""
    corpus = read_jsonl(corpus_path)
    queries = read_jsonl(queries_path)
    qrels: dict[str, set[str]] = {}
    with qrels_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            query_id, doc_id, _ = line.split("\t")
            qrels.setdefault(query_id, set()).add(doc_id)

    rankings: dict[str, list[str]] = {}
    for query in queries:
        scored = rank_corpus(query["text"], corpus)
        rankings[query["query_id"]] = [doc_id for doc_id, _ in scored[:top_k]]

    metrics = compute_retrieval_metrics(rankings, qrels)
    results = {
        "corpus_path": str(corpus_path),
        "queries_path": str(queries_path),
        "qrels_path": str(qrels_path),
        "corpus_count": len(corpus),
        "query_count": len(queries),
        "metrics": metrics,
    }
    write_json(output_path, results)
    return results


def main() -> int:
    """CLI 인자를 읽고 MedQuAD 검색 벤치마크를 실행한다."""
    parser = argparse.ArgumentParser(description="Run MedQuAD retrieval benchmark with lexical overlap baseline.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_DIR, help="Directory containing corpus, queries, and qrels")
    parser.add_argument("--output", type=Path, default=COMMON_ROOT / "data" / "evals" / "medquad_retrieval_results.json", help="Path to write results json")
    args = parser.parse_args()

    input_dir: Path = args.input_dir
    output_path: Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    results = run(
        corpus_path=input_dir / "medquad_corpus.jsonl",
        queries_path=input_dir / "medquad_queries.jsonl",
        qrels_path=input_dir / "medquad_qrels.tsv",
        output_path=output_path,
    )
    print(
        "MedQuAD retrieval complete. "
        f"R@1={results['metrics']['recall']['R@1']:.3f} "
        f"R@3={results['metrics']['recall']['R@3']:.3f} "
        f"R@5={results['metrics']['recall']['R@5']:.3f} MRR={results['metrics']['mrr']:.3f}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
