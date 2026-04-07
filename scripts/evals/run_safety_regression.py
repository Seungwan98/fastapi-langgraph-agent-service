from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from app.services.safety import sanitize_output, triage_message  # noqa: E402
from scripts.evals.common import ROOT as COMMON_ROOT, read_jsonl, write_json  # noqa: E402


DEFAULT_INPUT = COMMON_ROOT / "data" / "derived" / "eval_inputs" / "safety_regression_cases.jsonl"


def run(input_path: Path, output_path: Path) -> dict:
    """저장된 평가 케이스로 안전 및 마스킹 검사를 수행한다."""
    cases = read_jsonl(input_path)
    passed = []
    failed = []

    for case in cases:
        decision = triage_message(case["message"])
        sanitized, changed, _ = sanitize_output(case["message"])

        label_ok = decision.level.value == case["expected_label"]
        sanitize_ok = changed is case.get("expect_sanitized", False)

        if label_ok and sanitize_ok:
            passed.append(case["id"])
        else:
            failed.append(
                {
                    "id": case["id"],
                    "expected_label": case["expected_label"],
                    "actual_label": decision.level.value,
                    "expect_sanitized": case.get("expect_sanitized", False),
                    "sanitized": changed,
                    "sanitized_output": sanitized,
                }
            )

    result = {
        "input_path": str(input_path),
        "total": len(cases),
        "passed": len(passed),
        "failed": failed,
        "pass_rate": len(passed) / len(cases) if cases else 0.0,
    }
    write_json(output_path, result)
    return result


def main() -> int:
    """CLI 인자를 읽고 안전 회귀 테스트를 실행한다."""
    parser = argparse.ArgumentParser(description="Run safety regression suite.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Path to safety regression cases jsonl")
    parser.add_argument("--output", type=Path, default=COMMON_ROOT / "data" / "evals" / "safety_regression_results.json", help="Path to write results json")
    args = parser.parse_args()

    output_path: Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results = run(args.input, output_path)
    print(f"Safety regression complete. Pass rate={results['pass_rate']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
