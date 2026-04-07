# Dependency Rules

## Dependency Injection Rules

### Single composition root
의존성 주입 진입점은 아래 두 곳만 허용한다.
- `app/core/settings.py`
- `app/core/dependencies.py`

### Injection 방식
- FastAPI endpoint에서는 `Depends(...)`만 사용한다.
- service 생성자는 `Settings` 또는 명시적 collaborator를 인자로 받는다.
- 테스트에서는 `app.dependency_overrides` 또는 monkeypatch를 사용한다.

## Singleton Policy

### 허용되는 Singleton
다음만 허용한다.
1. `get_settings()` cache
2. service factory cache (`get_agent_service()` 경유)
3. service 내부의 lazy client cache (예: embedding client)

### 금지되는 Singleton
- module-level OpenAI client 인스턴스
- module-level database connection
- module-level mutable state dict/list
- 테스트 간 공유되는 fake service singleton

## External Dependency Rules

### Provider access
OpenAI/FHIR/public source 호출은 route에서 금지한다.
반드시 service adapter를 통해 접근한다.

### Environment access
`OPENAI_API_KEY`, `RAG_*`, `FHIR_*` 등의 환경 변수는
오직 `Settings`를 통해 읽는다.

### Adapter boundary
새 connector는 아래 계약을 가져야 한다.
- 입력 타입이 명시적일 것
- 실패 시 예외 또는 빈 결과 전략이 문서화될 것
- API 응답용 metadata shape를 안정적으로 제공할 것

## Repository Dependency Rules

- 새 패키지 추가는 기본 금지
- 꼭 필요하면 아래를 동시에 남긴다.
  - 왜 표준 라이브러리/기존 라이브러리로 안 되는지
  - 어느 레이어가 이 패키지에 의존하는지
  - 테스트에서 어떻게 격리할지
