# Backend Agent Guide

이 저장소는 FastAPI + LangGraph 기반 건강 불안 지원 백엔드다.

## Start here
- 문서 허브: `docs/README.md`
- 아키텍처 개요: `docs/ARCHITECTURE.md`
- 설계 원칙: `docs/design-docs/index.md`
- 제품/사용자 맥락: `docs/product-specs/index.md`
- 실행 계획 현황: `docs/PLANS.md`
- 신뢰성/보안 기준: `docs/RELIABILITY.md`, `docs/SECURITY.md`

## Working rules
- 라우터는 얇게 유지하고 비즈니스 로직은 `app/services/`에 둔다.
- 환경 변수는 `app/core/settings.py`와 `Depends` 체인으로만 주입한다.
- 실제 런타임 RAG 원본은 `knowledge-base/` 에 두고, `docs/` 는 문서 전용으로 유지한다.
- 새 외부 연동은 `app/services/*_connector.py` 또는 전용 adapter 파일에 분리한다.
- 생성 문서는 `docs/generated/`에 두고, 사람이 쓴 기획/설계 문서와 섞지 않는다.
- 실행 중인 일은 `docs/exec-plans/active/`, 완료된 일은 `docs/exec-plans/completed/` 아래에 둔다.
- 변경 후 최소 `pytest -q`로 회귀를 확인한다.

## Documentation map
- `docs/design-docs/` — 핵심 설계 원칙, 시스템 사고방식, 구조 결정 배경
- `docs/product-specs/` — 사용자 흐름, 기능 명세, 제품 의도
- `docs/exec-plans/` — 진행 중/완료된 실행 계획과 기술 부채
- `docs/generated/` — 생성 산출물, 스키마, 자동 생성 참고자료
- `docs/references/` — 외부 도구/플랫폼 참고 문서
- `knowledge-base/` — 런타임 RAG 지식 원본
- `docs/rules/`, `docs/tests/`, `docs/architecture/`, `docs/operations/` — 기존 세부 운영 문서 보관

## Frontend reference
- 경로: `/Users/seungwan/xcode/FE`
- 개발 URL: `http://localhost:5173`
- 프록시: `/api`, `/health` → `http://localhost:8000`
