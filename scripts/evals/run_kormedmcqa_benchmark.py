from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from scripts.evals.common import ROOT as COMMON_ROOT, read_jsonl, write_json


DEFAULT_INPUT = COMMON_ROOT / "data" / "derived" / "eval_inputs" / "kormed_evalset.jsonl"


def baseline_predict(choices: list[str]) -> int:
    """가장 긴 선택지를 결정적 기준 답안으로 고른다."""
    if not choices:
        return -1
    lengths = [len(choice) for choice in choices]
    return lengths.index(max(lengths))


def run(input_path: Path, output_path: Path) -> dict:
    """한국어 MCQ 평가셋에서 결정적 기준 모델을 벤치마크한다."""
    rows = read_jsonl(input_path)
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row.get("config", "unknown"), row.get("split", "unknown"))].append(row)

    results: dict[str, dict] = {}
    for (config, split), samples in grouped.items():
        total = len(samples)
        correct = 0
        for sample in samples:
            pred = baseline_predict(sample.get("choices", []))
            if pred == sample.get("answer_index"):
                correct += 1
        key = f"{config}:{split}"
        results[key] = {"total": total, "correct": correct, "accuracy": (correct / total if total else 0.0)}

    overall_total = sum(block["total"] for block in results.values())
    overall_correct = sum(block["correct"] for block in results.values())
    aggregate = {
        "overall_total": overall_total,
        "overall_correct": overall_correct,
        "overall_accuracy": overall_correct / overall_total if overall_total else 0.0,
    }

    payload = {
        "input_path": str(input_path),
        "by_config_split": results,
        "aggregate": aggregate,
    }
    write_json(output_path, payload)
    return payload


def main() -> int:
    """CLI 인자를 읽고 KorMedMCQA 벤치마크를 실행한다."""
    parser = argparse.ArgumentParser(description="Run KorMedMCQA deterministic benchmark.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Path to kormed evalset jsonl")
    parser.add_argument("--output", type=Path, default=COMMON_ROOT / "data" / "evals" / "kormed_results.json", help="Path to write results json")
    args = parser.parse_args()

    output_path: Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results = run(args.input, output_path)
    print(f"KorMed benchmark complete. Overall accuracy={results['aggregate']['overall_accuracy']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
