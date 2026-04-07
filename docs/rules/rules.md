# Rules

이 문서는 이 프로젝트에서 AI가 코드를 작성할 때 따라야 하는 **Harness Engineering 기반 제약 문서의 시작점**이다.

## 1. 프로젝트 분석

### 현재 아키텍처
이 프로젝트는 **Layered Modular Monolith + LangGraph Orchestration** 구조다.

- `app/api/routes/` — HTTP entrypoint
- `app/core/` — settings, dependency injection composition root
- `app/services/` — agent orchestration, safety, retrieval, external integration
- `app/schemas/` — API contract
- `frontend/` — React/Vite client

현재 동작 흐름은 다음과 같다.

```text
Route -> Service -> Retrieval / Connector / Provider
```

세부적으로는 아래 패턴이 섞여 있다.
- **Layered Architecture**: route / service / schema 분리
- **Workflow Orchestration**: `AgentService`가 LangGraph 상태 전이를 관리

### 사용 기술
#### Backend
- Python
- FastAPI
- Pydantic v2 / pydantic-settings
- LangChain / LangGraph
- OpenAI (`ChatOpenAI`, `OpenAIEmbeddings`)
- SQLite checkpoint
- pytest

#### Frontend
- React 18
- TypeScript
- Vite
- Axios

### 잠재적인 문제점
1. **God Service 위험**
   - `app/services/agent_graph.py`가 prompt, retrieval, graph, provider, patient context를 모두 안고 있다.
2. **Typed Boundary 부족**
   - 내부에서 `dict[str, Any]`와 state dict 사용 비중이 크다.
3. **Route-layer 정책 집중**
   - triage, fallback, sanitize orchestration이 route에 몰려 있다.
4. **DI / 설정 수명주기 복잡도**
   - `_get_agent_service_instance()`가 너무 많은 primitive 설정값을 직접 받는다.
5. **성능 병목 가능성**
   - `AgentService.invoke()` lock 기반 직렬화가 병목이 될 수 있다.
6. **문서 탐색 비용**
   - 구조/검증/운영 문서가 섞이면 변경 기준점이 흐려진다.

## 2. 이 프로젝트의 핵심 제약 목표
1. Route를 얇게 유지해 정책 분산을 막는다.
2. Agent orchestration과 integration adapter를 분리해 God Service화를 막는다.
3. Settings/DI 경로를 하나로 고정해 환경 의존성 누수를 막는다.
4. Safety / Retrieval / Fallback 계약을 테스트로 잠가 회귀를 막는다.

## 3. 읽는 순서
1. `docs/rules/rules.md`
2. `docs/rules/architecture-rules.md`
3. `docs/rules/code-rules.md`
4. `docs/rules/dependency-rules.md`
5. `docs/rules/forbidden-actions.md`
6. `docs/tests/feedback-loop.md`

## 4. Non-negotiables
- FastAPI route는 입력/출력 매핑만 담당한다.
- 비즈니스 규칙은 `app/services/`에만 둔다.
- 환경 변수 직접 접근은 `app/core/settings.py` 밖에서 금지한다.
- 안전성(triage/sanitize) 경로는 우회 금지다.
- 검증 없이 완료로 보고하지 않는다.
