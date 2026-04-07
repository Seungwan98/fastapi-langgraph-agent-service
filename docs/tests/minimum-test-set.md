# Minimum Test Set

## 반드시 유지할 단위 테스트 세트

### 1. Safety
대상: `app/services/safety.py`

필수 시나리오:
- RED: chest pain + shortness of breath
- RED: self-harm / prompt override / secret request
- AMBER: persistent fever / vomiting / allergic reaction
- GREEN: 일반 대화
- sanitizer: `api key`, `password`, `token`, `sk-...` 마스킹

현재 매핑:
- `tests/test_safety_regression.py`
- `tests/evals/test_safety_regression.py`

### 2. Agent Graph
대상: `app/services/agent_graph.py`

필수 시나리오:
- retrieval query가 최근 대화로 구성됨
- rewrite 실패 시 원문으로 fallback
- answer prompt에 base system prompt 포함
- retrieval context가 있으면 wrapper prompt 포함
- local/public/FHIR source merge 유지

현재 매핑:
- `tests/test_agent_graph.py`

### 3. Retriever
대상: `app/services/retriever.py`

필수 시나리오:
- chunk 분할 규칙 유지
- metadata frontmatter 파싱 유지
- ranking이 red-flag / reassure 정책을 반영
- source metadata shape 유지
- index build 결과 payload shape 유지

현재 매핑:
- `tests/test_retriever.py`

### 4. API Contract
대상: `app/api/routes/agent.py`, `app/api/routes/rag.py`, `app/api/routes/health.py`

필수 시나리오:
- API key 없으면 503
- RED triage면 400
- 성공 응답 shape 유지
- fallback metadata 유지
- retrieval metadata 유지
- patient_id 전달 유지
- RAG rebuild admin token 검증 유지

현재 매핑:
- `tests/test_agent_api.py`
- `tests/test_rag_api.py`
- `tests/test_health.py`
- `tests/test_health_context_sources.py`

## 최소 실행 명령
```bash
pytest -q \
  tests/test_safety_regression.py \
  tests/test_retriever.py \
  tests/test_agent_graph.py \
  tests/test_agent_api.py \
  tests/test_rag_api.py
```
