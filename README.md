# FastAPI LangGraph Agent Service

건강 불안 대화를 지원하는 AI 에이전트 백엔드 프로젝트입니다. FastAPI, LangChain, LangGraph를 기반으로 만들었고, React 프론트엔드와 함께 동작합니다.

## 프로젝트 소개

- FastAPI로 API 서버 구성
- LangChain + LangGraph로 대화형 에이전트 구성
- SQLite 체크포인트로 대화 흐름 유지
- 선택형 RAG(JSON 인덱스 + OpenAI embeddings)로 큐레이션 문서 검색
- RED / AMBER / GREEN 트리아지로 위험 메시지 선별
- React + Vite 프론트엔드 제공
- AWS EC2 + Docker 배포, Vercel 프론트 배포 완료

## 주요 기능

### 1. 대화형 에이전트
- `POST /api/v1/agent/invoke` 로 사용자 메시지 처리
- `thread_id` 기반으로 대화 맥락 유지
- OpenAI 모델 응답을 표준 JSON 형태로 반환

### 2. 안전성 필터
- 응급/위험 상황은 `RED` 로 차단
- 주의가 필요한 증상은 `AMBER` 로 표시
- 일반 요청은 `GREEN` 으로 정상 처리
- 출력에 API Key, 비밀번호 같은 민감 정보가 있으면 자동 마스킹

### 3. 운영 편의 기능
- `X-Request-ID`, `X-Latency-Ms` 헤더 추가
- OpenAI 장애 시 fallback 메시지 반환
- Docker 기반 재배포 가능

## 기술 스택

| 구분 | 기술 |
|---|---|
| Backend | FastAPI |
| AI Agent | LangChain, LangGraph |
| LLM | OpenAI GPT-4o-mini |
| Database | SQLite |
| Frontend | React, TypeScript, Vite |
| Test | pytest |
| Deploy | Docker, AWS EC2, Vercel |

## 프로젝트 구조

```text
BE/
├── app/
│   ├── main.py              # FastAPI 앱 팩토리
│   ├── api/routes/          # health, agent 라우터
│   ├── core/                # settings, dependency
│   ├── services/            # agent_graph, safety, tools
│   └── schemas/             # 요청/응답 스키마
├── frontend/                # React 프론트엔드
├── docs/                    # 규칙/검증/아키텍처/운영 문서
├── scripts/                 # 평가/데이터 스크립트
└── tests/                   # 테스트 코드
```

## 로컬 실행 방법

### 1. 백엔드 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

`.env` 에는 최소한 아래 값이 필요합니다.

```bash
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
CHECKPOINT_DB_PATH=data/agent_checkpoints.sqlite
RAG_ENABLED=false
RAG_INDEX_PATH=data/rag_index.json
RAG_SOURCE_DIR=knowledge-base
RAG_EMBEDDING_MODEL=text-embedding-3-small
RAG_TOP_K=4
RAG_MIN_SCORE=0.2
RAG_CHUNK_SIZE=800
RAG_CHUNK_OVERLAP=120
RAG_HISTORY_TURNS=3
RAG_QUERY_REWRITE_ENABLED=false
RAG_ADMIN_TOKEN=
PUBLIC_MEDICAL_ENABLED=false
PUBLIC_MEDICAL_SOURCE_PATH=data/public_medical_reference.json
PUBLIC_MEDICAL_BASE_URL=
PUBLIC_MEDICAL_TOP_K=2
FHIR_ENABLED=false
FHIR_SOURCE_PATH=data/fhir_patient_context.json
FHIR_BASE_URL=
FHIR_BEARER_TOKEN=
FHIR_OBSERVATION_LIMIT=5
```

### 2. 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

### RAG 인덱스 생성

```bash
python3 scripts/build_rag_index.py --input-dir knowledge-base --output data/rag_index.json
```

`knowledge-base/` 아래에 큐레이션된 참고 문서를 넣고, 런타임에서는 `RAG_ENABLED=true`로 활성화합니다. 기본 예시 문서도 함께 포함되어 있습니다. 후속 질문 검색 품질은 `RAG_HISTORY_TURNS`로 조절할 수 있고, 필요하면 `RAG_QUERY_REWRITE_ENABLED=true`로 LLM 기반 질의 재작성도 켤 수 있습니다.

## 배포 주소

- 프론트엔드: `https://frontend-nu-seven-50.vercel.app`
- 백엔드 Health: `http://13.60.28.115:8000/health/live`
- 백엔드 Swagger: `http://13.60.28.115:8000/docs`

## API 요약

### Health
- `GET /health/live`
- `GET /health/ready`

### Agent
- `POST /api/v1/agent/invoke`

### RAG
- `POST /api/v1/rag/rebuild` (requires `X-Admin-Token`)

요청 예시:

```json
{
  "message": "요즘 건강 걱정이 많아요",
  "thread_id": "optional-thread-id"
}
```

응답 예시:

```json
{
  "output": "건강에 대한 걱정이 있으시군요. 어떤 점이 가장 신경 쓰이시나요?",
  "thread_id": "thread-id",
  "model": "gpt-4o-mini",
  "metadata": {
    "triage_level": "GREEN",
    "triage_reasons": [],
    "fallback_used": false,
    "guardrail_sanitized": false
  }
}
```

## 테스트

```bash
python3 -m pytest -q
```

## 문서

- `docs/README.md`
- `docs/rules/rules.md`
- `docs/tests/feedback-loop.md`
- `docs/architecture/overview.md`
- `docs/architecture/api.md`
- `docs/operations/deployment.md`
- `AGENTS.md`

## 비고

- 현재 프론트는 Vercel rewrites로 백엔드에 연결됩니다.
- 백엔드는 HTTP로 배포되어 있어서, 이후엔 도메인 + HTTPS 적용을 권장합니다.
