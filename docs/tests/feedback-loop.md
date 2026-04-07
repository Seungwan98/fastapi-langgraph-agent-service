# Feedback Loop

## 목적
AI가 만든 변경이 이 프로젝트의 핵심 계약을 깨지 않았는지 **컴파일 → 테스트 → 로직 검증 → 수정 루프**로 확인한다.

## 검증 순서
1. **정적 확인** — import / 문법 / 파일 배치 확인
2. **핵심 단위 테스트** — safety, retriever, agent graph, API contract
3. **회귀 테스트** — 전체 pytest
4. **문서/계약 동기화 확인** — README, docs, schema 경로 확인

## 필수 게이트
아래 4개를 모두 통과해야 완료로 간주한다.
- `python -m compileall app tests`
- 최소 테스트 세트 통과
- `pytest -q` 통과
- 변경된 문서 경로와 README/AGENTS 링크 일치

## 핵심 검증 대상
1. `RED/AMBER/GREEN` triage가 유지되는가
2. provider 실패 시 fallback contract가 유지되는가
3. retrieval metadata shape가 유지되는가
4. patient context / public reference merge가 깨지지 않는가
5. route가 여전히 thin한가

## Validation Checklist

### 1. Compile Validation
```bash
python -m compileall app tests
```
확인 목적:
- import error
- syntax error
- 잘못된 파일 이동/이름 변경

### 2. Targeted Validation
```bash
pytest -q tests/test_safety_regression.py
pytest -q tests/test_retriever.py
pytest -q tests/test_agent_graph.py
pytest -q tests/test_agent_api.py
pytest -q tests/test_rag_api.py
```
확인 목적:
- 변경한 레이어의 직접 회귀 확인

### 3. Full Regression
```bash
pytest -q
```
확인 목적:
- 숨은 계약 파손 확인

### 4. Documentation Validation
아래를 수동 또는 grep으로 확인한다.
- README 문서 링크가 실제 경로를 가리키는가
- AGENTS.md가 새 rules/tests 경로를 가리키는가
- `docs/knowledge/` 경로가 유지되는가
- 이동된 문서 간 내부 링크가 끊기지 않았는가

예시 명령:
```bash
find docs -maxdepth 3 -type f | sort
rg -n "docs/(ARCHITECTURE|API|DEPLOYMENT|CONVENTIONS|data-plan1|plan1-portfolio-playbook|progress-diagram)\.md" README.md AGENTS.md docs || true
```

## Auto-fix Strategy

### Loop
1. 실패를 분류한다.
2. 가장 아래 레이어부터 고친다.
3. 실패한 테스트만 먼저 재실행한다.
4. 통과하면 상위 테스트 범위를 넓힌다.
5. 마지막에 전체 회귀를 다시 돈다.

### Failure Classification
#### A. Compile 실패
원인 우선순위:
1. import path 오류
2. 파일 이동 후 경로 미갱신
3. 순환 참조
4. 타입/문법 오류

수정 원칙:
- route/service/schema 책임 재분리
- 임시 import hack 금지

#### B. API Contract 실패
원인 우선순위:
1. schema shape 변경
2. metadata field 누락
3. fallback/triage HTTP mapping 변경

수정 원칙:
- 먼저 `app/schemas/`와 route response 생성부를 맞춘다.
- 테스트 fixture를 그 다음에 맞춘다.

#### C. Safety 실패
원인 우선순위:
1. regex/pattern 변경
2. RED/AMBER precedence 깨짐
3. sanitizer 누락

수정 원칙:
- safety 실패는 빠른 기능 추가보다 우선 복구한다.
- rule 수정 시 반드시 regression test도 같이 갱신한다.

#### D. Retrieval / Graph 실패
원인 우선순위:
1. source metadata shape drift
2. retrieval ranking rule drift
3. prompt assembly drift
4. connector merge drift

수정 원칙:
- score/ranking 로직은 deterministic fixture로 먼저 고친다.
- prompt 변경은 `tests/test_agent_graph.py` 기대값과 같이 관리한다.

## Stop Condition
아래가 모두 만족될 때만 루프 종료:
- compile 성공
- targeted tests 성공
- full pytest 성공
- README / AGENTS / docs 링크 정합성 확인
