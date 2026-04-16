# Architecture Hub

이 문서는 이 저장소의 아키텍처 진입점이다.

## Read this first
- 시스템 개요: `docs/architecture/overview.md`
- API 계약: `docs/architecture/api.md`
- 설계 원칙: `docs/design-docs/core-beliefs.md`
- 신뢰성 기준: `docs/RELIABILITY.md`
- 보안 기준: `docs/SECURITY.md`

## Current system summary
- FastAPI 라우터가 요청을 받고 안전성 트리아지 후 서비스 계층으로 전달한다.
- `AgentService` 가 LangGraph 기반 상태 흐름과 RAG 조회를 오케스트레이션한다.
- 대화 체크포인트는 기본적으로 SQLite에 저장된다.
- 런타임 지식 문서는 `knowledge-base/` 를 원본으로 사용한다.

## Deep links
- 상세 구조: `docs/architecture/overview.md`
- 배포/운영: `docs/operations/deployment.md`
- 테스트 루프: `docs/tests/feedback-loop.md`
- 코드/의존성 규칙: `docs/rules/`
