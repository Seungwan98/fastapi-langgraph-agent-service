# Forbidden Actions

이 항목들은 AI가 절대 하면 안 되는 작업이다.

## Safety
- `triage_message()` 호출을 제거하거나 우회하지 않는다.
- `sanitize_output()` 적용을 제거하거나 조건부로 약화하지 않는다.
- RED 요청을 정상 응답으로 바꾸지 않는다.

## Architecture
- route에서 OpenAI/FHIR/RAG를 직접 호출하지 않는다.
- `agent_graph.py`에 새 기능을 무한 누적하지 않는다.
- `dict[str, Any]`를 이유 없이 새 경계 타입으로 도입하지 않는다.

## Data / Privacy
- `.env`, API key, bearer token, patient identifier를 문서/fixture/로그에 하드코딩하지 않는다.
- 실제 PHI/민감정보를 `knowledge-base/`, `data/`, `tests/fixtures`에 저장하지 않는다.

## Dependency / State
- import 시점에 network call, DB open, index build를 실행하지 않는다.
- module global mutable state로 대화 상태를 저장하지 않는다.
- ad-hoc singleton을 추가하지 않는다.

## Docs / Repo Hygiene
- `knowledge-base/`에 운영 문서를 넣지 않는다.
- 문서 재배치 후 README/AGENTS 경로를 갱신하지 않은 채 두지 않는다.
- 테스트가 깨졌는데 문서만 맞다고 완료 처리하지 않는다.
