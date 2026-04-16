# Architecture Rules

## Allowed Patterns

### A. Route → Orchestrator → Adapter 흐름만 허용
허용되는 기본 흐름:

```text
FastAPI Route
  -> application/orchestration service
  -> domain/policy service
  -> external adapter / connector
```

현재 코드 기준 매핑:
- Route: `app/api/routes/*.py`
- Orchestrator: `app/services/agent_graph.py`
- Policy: `app/services/safety.py`
- Adapter: `app/services/retriever.py`, `app/services/fhir_connector.py`, `app/services/public_medical_reference.py`

### B. Thin Route 패턴만 허용
Route 파일은 아래만 담당한다.
- request schema 수신
- dependency resolve
- service call
- HTTP status mapping
- response schema 반환

### C. External integration isolation 허용
새 외부 연동은 반드시 아래 중 하나로 분리한다.
- `app/services/<provider>_connector.py`
- `app/services/<provider>_client.py`
- `app/services/<feature>_lookup.py`

### D. Typed boundary 허용
다음 경계에는 반드시 명시적 타입을 둔다.
- API request/response (`app/schemas/`)
- service 반환값
- retrieval source metadata
- connector output

가능하면 `dict[str, Any]` 대신 `dataclass` 또는 Pydantic 모델을 쓴다.

## Forbidden Patterns

### 절대 금지 1 — Route 안에 비즈니스 규칙 추가
금지 예시:
- symptom scoring
- retrieval ranking 조정
- prompt 텍스트 조립
- FHIR payload 해석

### 절대 금지 2 — Service에서 HTTP 개념 누수
`app/services/` 내부에서 아래를 직접 다루지 않는다.
- `APIRouter`
- `Request`
- `Response`
- `HTTPException`
- status code literal

### 절대 금지 3 — Settings 우회
`os.getenv()` 또는 `BaseSettings()` 직접 호출을 route/service 내부에서 금지한다.
설정은 오직:
- `app/core/settings.py`
- `app/core/dependencies.py`
를 통해서만 공급한다.

### 절대 금지 4 — 신규 기능을 `agent_graph.py`에 무조건 누적
아래 조건 중 하나라도 만족하면 파일 분리한다.
- 외부 시스템이 1개 추가됨
- 반환 metadata shape가 커짐
- prompt 조립 규칙이 별도 문단 수준으로 늘어남
- 테스트 픽스처가 3개 이상 새로 필요함

### 절대 금지 5 — RAG 지식과 운영 문서 혼합
`knowledge-base/`는 런타임 RAG 입력이다.
아래 문서를 넣지 않는다.
- 배포 가이드
- 회고/플레이북
- 시스템 설계 문서
- 임시 메모
