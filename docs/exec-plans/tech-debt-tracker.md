# Tech Debt Tracker

## Active debt items

### 1. Runtime retrieval storage is JSON-backed
- 현재 RAG 검색은 JSON 인덱스 + embedding 유사도 계산 방식이다.
- 문서 수가 커지면 전용 vector store 도입 검토가 필요하다.

### 2. Documentation split between legacy and new structure
- 기존 `docs/architecture/`, `docs/rules/`, `docs/tests/` 는 유지 중이다.
- 새 허브 문서를 통해 점진적으로 정리한다.

### 3. Deployment docs are AWS-heavy
- 로컬/개발 환경 기준 문서가 보강되었지만 운영 문서는 여전히 AWS 중심이다.
- 이후 실제 배포 방식에 맞춰 업데이트 필요하다.
