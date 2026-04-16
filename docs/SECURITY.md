# Security

## Baselines
- 민감 정보는 출력 단계에서 sanitize 한다.
- prompt injection/credential request 패턴은 triage 단계에서 차단한다.
- 외부 연동 토큰은 코드에 하드코딩하지 않는다.

## Source docs
- `docs/rules/forbidden-actions.md`
- `docs/rules/dependency-rules.md`
- `app/services/safety.py`
