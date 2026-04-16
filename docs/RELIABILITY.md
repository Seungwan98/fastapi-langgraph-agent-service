# Reliability

## Core expectations
- Health/readiness endpoint가 명확해야 한다.
- 실패 시 fallback 메시지와 안전한 응답 경로가 있어야 한다.
- 같은 `thread_id` 로 대화 연속성이 유지되어야 한다.

## Current mechanisms
- LangGraph checkpointing
- FastAPI health endpoints
- safety triage + response sanitization
