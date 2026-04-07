# Project Progress Diagram

이 문서는 현재 시스템의 런타임 구조, 안전성 분기, 데이터 파이프라인, 평가 파이프라인을 한 파일에 정리한 통합 다이어그램 문서다.

---

## 1) 런타임 아키텍처

```mermaid
flowchart LR
    U[사용자] --> FE[React 채팅 UI\nfrontend/src/App.tsx]
    FE -->|POST /api/v1/agent/invoke| API[FastAPI\napp/api/routes/agent.py]
    FE -->|GET /health/live\nGET /health/ready| H[헬스 체크\napp/api/routes/health.py]

    API --> T[Triage + Sanitizer\napp/services/safety.py]
    T -->|RED| BLOCK[요청 차단\nHTTP 400]
    T -->|AMBER/GREEN| SVC[AgentService\napp/services/agent_graph.py]

    SVC --> LG[LangGraph Graph]
    LG --> OA[OpenAI Model]
    LG <--> DB[(SQLite Checkpoint\ndata/agent_checkpoints.sqlite)]

    SVC -->|Provider Error| FB[Fallback Message\nAGENT_FALLBACK_MESSAGE]
    API --> META[metadata\ntriage/fallback/sanitizer/request_id]
```

## 2) 안전 분기 플로우 / Safety Decision Flow

```mermaid
flowchart TD
    A[Incoming message] --> B[triage_message]
    B -->|RED| C[Block request\nHTTP 400]
    B -->|AMBER| D[Invoke agent with caution metadata]
    B -->|GREEN| E[Invoke agent normal path]

    D --> F[sanitize_output]
    E --> F
    F --> G{Sensitive pattern found?}
    G -->|Yes| H[Replace with [REDACTED]\nmark guardrail_sanitized=true]
    G -->|No| I[Return original output]

    D --> J{Provider/model failure?}
    E --> J
    J -->|Yes| K[Return fallback response\nfallback_used=true]
    J -->|No| L[Return model response]
```

## 3) 데이터 부트스트랩 / Data Bootstrap Pipeline

```mermaid
flowchart LR
    S1[Synthea sample] --> P[prepare_plan1_datasets.py]
    S2[MedQuAD] --> P
    S3[EmpatheticDialogues] --> P
    S4[KorMedMCQA] --> P

    P --> RAW[data/datasets/plan1/raw/*]
    P --> N1[patients.jsonl]
    P --> N2[qa.jsonl]
    P --> N3[dialogues.jsonl]
    P --> N4[mcqa.jsonl]
    P --> M[manifest.json]

    M --> V[verify_plan1_datasets.py]
    V --> OK[Verification succeeded]
```

## 4) 평가 파이프라인 / Evaluation Pipeline

```mermaid
flowchart TD
    A[data/datasets/plan1/normalized/*] --> B[build_eval_inputs.py]
    B --> C[data/derived/eval_inputs/manifest.json]
    B --> D[triage_evalset.jsonl]
    B --> E[medquad_corpus/queries/qrels]
    B --> F[kormed_evalset.jsonl]
    B --> G[fallback_stress_cases.jsonl]
    B --> H[safety_regression_cases.jsonl]

    D --> R1[run_triage_eval.py]
    E --> R2[run_medquad_retrieval_benchmark.py]
    F --> R3[run_kormedmcqa_benchmark.py]
    G --> R4[run_fallback_stress.py]
    H --> R5[run_safety_regression.py]

    R1 --> SUM[run_portfolio.py]
    R2 --> SUM
    R3 --> SUM
    R4 --> SUM
    R5 --> SUM

    SUM --> OUT[data/evals/portfolio/plan1-local/portfolio_summary.json]
```

## 5) 현재 메트릭 / Current Metrics Snapshot

```mermaid
flowchart LR
    T[Triage\naccuracy=1.00\nmacro_f1=1.00]
    M[MedQuAD Retrieval\nR@1=0.00\nR@3=0.00\nR@5=0.00\nMRR=0.0083]
    K[KorMedMCQA\noverall_accuracy=0.20]
    F[Fallback Stress\npass_rate=1.00]
    S[Safety Regression\npass_rate=1.00]

    T --> DONE[Portfolio Summary]
    M --> DONE
    K --> DONE
    F --> DONE
    S --> DONE
```

## Key Artifact Paths
- Data manifest: `data/datasets/plan1/normalized/manifest.json`
- Eval input manifest: `data/derived/eval_inputs/manifest.json`
- Portfolio summary: `data/evals/portfolio/plan1-local/portfolio_summary.json`
- Narrative reference: `docs/data/plan1-portfolio-playbook.md`
