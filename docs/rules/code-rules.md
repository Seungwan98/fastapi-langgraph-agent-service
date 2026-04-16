# Code Rules

## Naming Rules

### Python
- module: `snake_case.py`
- class: `PascalCase`
- function / variable: `snake_case`
- constant: `UPPER_SNAKE_CASE`
- private helper: `_leading_underscore`

### API / Schema
- request model: `<Feature>Request`
- response model: `<Feature>Response`
- response metadata model: `<Feature>Metadata`
- exception type: `<Domain>Error`

### Test
- file: `tests/test_<unit>.py`
- test name: `test_<behavior>_<expected_result>`

## File Structure Rules

### app/api/routes/
허용:
- router 선언
- endpoint 함수
- schema import
- dependency import
- HTTP mapping

금지:
- regex rule 정의
- system prompt 정의
- retrieval scoring 정의
- provider client 생성

### app/services/
허용:
- orchestration
- domain rule
- connector / lookup / retriever
- provider adapter
- pure helper

규칙:
- 한 파일은 한 책임 축만 가진다.
- safety rule은 `safety.py`에만 둔다.
- retrieval ranking rule은 `retriever.py`에만 둔다.
- provider failure mapping은 orchestrator 또는 전용 error mapper에만 둔다.

### app/schemas/
허용:
- API contract 모델
- response metadata 모델

금지:
- network call
- service import
- environment access

### docs/
- `docs/rules/` — 구조 제약
- `docs/tests/` — 검증 시스템
- `docs/architecture/` — 시스템 설명
- `docs/operations/` — 배포/운영
- `docs/data/` — 데이터/평가
- `docs/diagrams/` — 시각화
- `knowledge-base/` — RAG 문서만 저장

## Implementation Rules

1. 새 endpoint를 만들면 아래 4개를 같이 만든다.
   - route
   - schema
   - service or adapter
   - test

2. 새 metadata field를 API에 추가하면 아래를 같이 수정한다.
   - `app/schemas/*`
   - response 생성부
   - API test
   - API 문서

3. 문자열 기반 정책(system prompt, safety copy, fallback copy)은
   - route가 아니라 service 또는 settings에 둔다.

4. import 시 사이클이 생기면 임시 import hack을 넣지 말고 파일 책임을 다시 자른다.
