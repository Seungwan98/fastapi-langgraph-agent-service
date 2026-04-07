# Backend Agent Guide

이 저장소는 FastAPI + LangGraph 기반 건강 불안 지원 백엔드다.

## Start here
- 구조 제약: `docs/rules/rules.md`
- 검증 루프: `docs/tests/feedback-loop.md`
- 시스템 개요: `docs/architecture/overview.md`
- API 계약: `docs/architecture/api.md`

## Working rules
- 라우터는 얇게 유지하고 비즈니스 로직은 `app/services/`에 둔다.
- 환경 변수는 `app/core/settings.py`와 `Depends` 체인으로만 주입한다.
- `docs/knowledge/`는 RAG 원본 지식 경로이므로 임의로 이동하지 않는다.
- 새 외부 연동은 `app/services/*_connector.py` 또는 전용 adapter 파일에 분리한다.
- 변경 후 최소 `pytest -q`로 회귀를 확인한다.

## Frontend reference
- 경로: `/Users/seungwan/xcode/FE`
- 개발 URL: `http://localhost:5173`
- 프록시: `/api`, `/health` → `http://localhost:8000`
