# Core Beliefs

## 1. Safety-first health support
- 이 서비스는 진단 시스템이 아니라 건강 불안 지원 대화 시스템이다.
- 응급 징후는 답변 생성보다 먼저 차단하거나 상향 안내해야 한다.

## 2. Thin routers, explicit services
- FastAPI 라우터는 입출력과 HTTP 책임만 가진다.
- 비즈니스 로직은 `app/services/` 에 집중한다.

## 3. Grounded responses over free-form generation
- 가능한 한 큐레이션된 지식과 명시적 컨텍스트를 바탕으로 답변한다.
- 런타임 RAG 원본은 `knowledge-base/` 이며, 이 경로는 설정과 문서에서 일관되게 유지한다.

## 4. Config-driven integrations
- 외부 연동은 설정 기반으로 켜고 끈다.
- 환경 변수 주입은 `app/core/settings.py` 와 dependency chain으로만 처리한다.

## 5. Verify after every meaningful change
- 코드 변경 뒤에는 최소 pytest 회귀 확인이 필요하다.
- 문서 구조 변경도 링크와 경로가 깨지지 않았는지 확인한다.
