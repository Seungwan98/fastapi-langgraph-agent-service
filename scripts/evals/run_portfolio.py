from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from scripts.evals import build_eval_inputs  # noqa: E402
from scripts.evals import run_fallback_stress, run_kormedmcqa_benchmark, run_medquad_retrieval_benchmark, run_safety_regression, run_triage_eval  # noqa: E402
from scripts.evals.common import ROOT as COMMON_ROOT, write_json  # noqa: E402


DEFAULT_INPUT_DIR = COMMON_ROOT / "data" / "derived" / "eval_inputs"
DEFAULT_EVALS_DIR = COMMON_ROOT / "data" / "evals" / "portfolio"


def main() -> int:
    """전체 평가 스위트를 실행하고 요약 보고서를 저장한다."""
    parser = argparse.ArgumentParser(description="Run full portfolio evaluation suite.")
    parser.add_argument("--run-id", default="plan1-run", help="Run identifier for output grouping")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR, help="Directory containing derived eval inputs")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_EVALS_DIR, help="Base directory for eval results")
    args = parser.parse_args()

    run_dir: Path = args.output_dir / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    if not args.input_dir.exists():
        print("Derived inputs missing. Building...")
        build_eval_inputs.build_all(args.input_dir)

    triage_results_path = run_dir / "triage_results.json"
    triage_results = run_triage_eval.run(args.input_dir / "triage_evalset.jsonl", triage_results_path)

    medquad_results_path = run_dir / "medquad_retrieval_results.json"
    medquad_results = run_medquad_retrieval_benchmark.run(
        corpus_path=args.input_dir / "medquad_corpus.jsonl",
        queries_path=args.input_dir / "medquad_queries.jsonl",
        qrels_path=args.input_dir / "medquad_qrels.tsv",
        output_path=medquad_results_path,
    )

    kormed_results_path = run_dir / "kormed_results.json"
    kormed_results = run_kormedmcqa_benchmark.run(args.input_dir / "kormed_evalset.jsonl", kormed_results_path)

    fallback_results_path = run_dir / "fallback_stress_results.json"
    fallback_results = run_fallback_stress.run(args.input_dir / "fallback_stress_cases.jsonl", fallback_results_path)

    safety_results_path = run_dir / "safety_regression_results.json"
    safety_results = run_safety_regression.run(args.input_dir / "safety_regression_cases.jsonl", safety_results_path)

    summary = {
        "run_id": args.run_id,
        "input_dir": str(args.input_dir),
        "results_dir": str(run_dir),
        "triage": {
            "accuracy": triage_results["metrics"]["accuracy"],
            "macro_f1": triage_results["metrics"]["macro"]["f1"],
            "path": str(triage_results_path),
            "count": triage_results["count"],
        },
        "medquad_retrieval": {
            "R@1": medquad_results["metrics"]["recall"]["R@1"],
            "R@3": medquad_results["metrics"]["recall"]["R@3"],
            "R@5": medquad_results["metrics"]["recall"]["R@5"],
            "MRR": medquad_results["metrics"]["mrr"],
            "path": str(medquad_results_path),
        },
        "kormed": {
            "overall_accuracy": kormed_results["aggregate"]["overall_accuracy"],
            "path": str(kormed_results_path),
        },
        "fallback_stress": {
            "pass_rate": fallback_results["pass_rate"],
            "path": str(fallback_results_path),
        },
        "safety_regression": {
            "pass_rate": safety_results["pass_rate"],
            "path": str(safety_results_path),
            "failed": safety_results["failed"],
        },
    }

    summary_path = run_dir / "portfolio_summary.json"
    write_json(summary_path, summary)
    print(f"Portfolio run {args.run_id} complete. Summary written to {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
