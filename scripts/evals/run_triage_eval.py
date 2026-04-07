from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from app.services.safety import TriageLevel, triage_message  # noqa: E402
from scripts.evals.common import ROOT as COMMON_ROOT, classification_report, compute_confusion_matrix, read_jsonl, write_json


DEFAULT_INPUT = COMMON_ROOT / "data" / "derived" / "eval_inputs" / "triage_evalset.jsonl"


def run(input_path: Path, output_path: Path) -> dict:
    """라벨이 있는 데이터셋으로 triage 예측을 평가한다."""
    rows = read_jsonl(input_path)
    labels = [row["expected_label"] for row in rows]
    predictions: list[str] = []
    for row in rows:
        decision = triage_message(row["message"])
        predictions.append(decision.level.value)

    class_order = [level.value for level in TriageLevel]
    confusion = compute_confusion_matrix(labels, predictions, class_order)
    report = classification_report(confusion, class_order)

    results = {
        "input_path": str(input_path),
        "count": len(rows),
        "confusion_matrix": confusion,
        "metrics": report,
    }
    write_json(output_path, results)
    return results


def main() -> int:
    """CLI 인자를 읽고 triage 평가를 실행한다."""
    parser = argparse.ArgumentParser(description="Run triage evaluation.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Path to triage evalset jsonl")
    parser.add_argument("--output", type=Path, default=COMMON_ROOT / "data" / "evals" / "triage_results.json", help="Path to write results json")
    args = parser.parse_args()

    output_path: Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results = run(args.input, output_path)
    print(f"Triage evaluation complete. Accuracy={results['metrics']['accuracy']:.3f} written to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
