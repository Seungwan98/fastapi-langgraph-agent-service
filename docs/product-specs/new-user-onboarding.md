# New User Onboarding

## Target user
- 건강에 대한 걱정이 크지만 지금 당장 무엇을 해야 할지 정리되지 않은 사용자

## First session goals
1. 사용자의 불안을 진정시키는 톤을 제공한다.
2. 응급 상황이면 즉시 적절한 안내로 분기한다.
3. 일반 상황이면 증상/걱정/다음 행동을 구조화하도록 돕는다.

## Product expectations
- 사용자는 진단이 아니라 방향성과 정리된 질문 리스트를 기대한다.
- 시스템은 의료 전문가 대체가 아니라 안전한 지원 대화 역할을 수행한다.

## Current backend touchpoints
- `POST /api/v1/agent/invoke`
- safety triage
- RAG grounded answer generation
