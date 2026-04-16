# DB Schema

이 문서는 현재 저장소에서 사용하는 주요 저장 구조를 정리한 생성/파생 문서다.

## 1. Conversation checkpoint storage
- 기본 경로: `data/agent_checkpoints.sqlite`
- 용도: LangGraph 체크포인트 저장
- 역할: 같은 `thread_id` 로 이어지는 대화 상태 복원

## 2. RAG index storage
- 기본 경로: `data/rag_index.json`
- 용도: 문서 chunk, embedding, 메타데이터 저장
- 참고: 현재는 전용 VectorDB가 아니라 JSON 기반 인덱스다.

## 3. Optional local data sources
- `data/public_medical_reference.json`
- `data/fhir_patient_context.json`

## Refresh sources
- 시스템 구조: `docs/architecture/overview.md`
- 구현 코드: `app/services/retriever.py`, `app/services/agent_graph.py`
