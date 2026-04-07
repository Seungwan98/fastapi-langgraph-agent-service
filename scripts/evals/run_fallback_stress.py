from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from app.core.dependencies import clear_agent_service_cache, get_agent_service  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services.errors import ModelProviderError  # noqa: E402
from scripts.evals.common import ROOT as COMMON_ROOT, read_jsonl, write_json  # noqa: E402


DEFAULT_INPUT = COMMON_ROOT / "data" / "derived" / "eval_inputs" / "fallback_stress_cases.jsonl"


class FailingAgentService:
    def __init__(self, *, model: str = "fallback-model"):
        """항상 실패하는 가짜 에이전트 서비스를 초기화한다."""
        self.model = model

    def invoke(self, message: str, thread_id: str | None = None) -> dict[str, str]:
        """폴백 경로를 강제로 타게 하기 위해 프로바이더 오류를 발생시킨다."""
        raise ModelProviderError("forced failure", thread_id=thread_id or "fallback-thread", model=self.model)


def run(input_path: Path, output_path: Path) -> dict:
    """강제 실패 상황에서 폴백 스트레스 케이스를 API로 실행한다."""
    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    clear_agent_service_cache()
    app.dependency_overrides[get_agent_service] = lambda: FailingAgentService()
    client = TestClient(app)

    cases = read_jsonl(input_path)
    passes = 0
    for case in cases:
        response = client.post("/api/v1/agent/invoke", json={"message": case.get("message", ""), "thread_id": case.get("id")})
        if response.status_code != 200:
            continue
        data = response.json()
        meta = data.get("metadata", {})
        if meta.get("fallback_used") and data.get("output") == get_settings().agent_fallback_message:
            passes += 1

    app.dependency_overrides = {}
    clear_agent_service_cache()

    result = {
        "input_path": str(input_path),
        "total": len(cases),
        "passed": passes,
        "pass_rate": passes / len(cases) if cases else 0.0,
    }
    write_json(output_path, result)
    return result


def main() -> int:
    """CLI 인자를 읽고 폴백 스트레스 하네스를 실행한다."""
    parser = argparse.ArgumentParser(description="Run fallback stress harness against agent API.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Path to fallback stress cases jsonl")
    parser.add_argument("--output", type=Path, default=COMMON_ROOT / "data" / "evals" / "fallback_stress_results.json", help="Path to write results json")
    args = parser.parse_args()

    output_path: Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results = run(args.input, output_path)
    print(f"Fallback stress complete. Pass rate={results['pass_rate']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
