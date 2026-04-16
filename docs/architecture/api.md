# API Reference

## Base URL

```
Development: http://localhost:8000
Production:  http://<EC2-IP>:8000
```

## Swagger UI

Interactive API documentation:
```
http://localhost:8000/docs
```

---

## Endpoints

### Health Check

#### GET /health/live

Liveness probe - always returns 200 if server is running.

**Response:**
```json
{
  "status": "ok"
}
```

**Status Codes:**
- `200 OK`: Server is alive

---

#### GET /health/ready

Readiness probe - checks if service is ready to accept requests.

**Response (Ready):**
```json
{
  "status": "ready"
}
```

**Response (Not Ready):**
```json
{
  "detail": "OPENAI_API_KEY is not configured"
}
```

**Status Codes:**
- `200 OK`: Ready (OPENAI_API_KEY configured)
- `503 Service Unavailable`: Not ready

---

### Agent Invocation

#### POST /api/v1/agent/invoke

Main endpoint for AI agent conversation.

**Request Body:**
```json
{
  "message": "string",      // Required: User input message
  "thread_id": "string"     // Optional: Conversation ID for context
}
```

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/v1/agent/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "message": "요즘 건강걱정이 많아요",
    "thread_id": "user-123"
  }'
```

**Success Response (200):**
```json
{
  "output": "건강에 대한 걱정이 있으시군요. 어떤 점이 가장 신경 쓰이시나요?",
  "thread_id": "user-123",
  "model": "gpt-4o-mini",
  "metadata": {
    "triage_level": "GREEN",
    "triage_reasons": [],
    "fallback_used": false,
    "guardrail_sanitized": false,
    "sanitizer_reasons": [],
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "retrieval_used": true,
    "retrieval_query": "headache for two weeks\nwhat should I ask my doctor",
    "retrieval_query_rewritten": true,
    "retrieved_sources": [
      {
        "chunk_id": "faq-chunk-1",
        "source": "knowledge-base/faq.md",
        "title": "FAQ",
        "score": 0.91
      }
    ]
  }
}
```

**Safety Block Response (400 - RED):**
```json
{
  "detail": {
    "message": "Request blocked by safety triage",
    "reasons": ["possible cardiopulmonary emergency"]
  }
}
```

**Not Ready Response (503):**
```json
{
  "detail": "OPENAI_API_KEY is not configured; set it and retry"
}
```

**Status Codes:**
- `200 OK`: Success
- `400 Bad Request`: Blocked by safety triage (RED level)
- `503 Service Unavailable`: OpenAI API key not configured
- `500 Internal Server Error`: Model error (fallback used)

---


### RAG Administration

#### POST /api/v1/rag/rebuild

Rebuilds the JSON RAG index from the configured knowledge directory.

**Headers:**
```
X-Admin-Token: <RAG_ADMIN_TOKEN>
```

**Success Response (200):**
```json
{
  "status": "ok",
  "document_count": 3,
  "chunk_count": 8,
  "output_path": "data/rag_index.json",
  "embedding_model": "text-embedding-3-small",
  "chunk_size": 800,
  "chunk_overlap": 120
}
```

**Status Codes:**
- `200 OK`: Rebuild succeeded
- `400 Bad Request`: Missing knowledge files or invalid build parameters
- `403 Forbidden`: Invalid admin token
- `404 Not Found`: Knowledge directory missing
- `503 Service Unavailable`: RAG admin rebuild not configured

---

## Schemas

### AgentInvokeRequest

```json
{
  "message": "string",    // Required, min length: 1
  "thread_id": "string"   // Optional, UUID format
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | User input message |
| `thread_id` | string | No | Conversation identifier for context continuity |

### AgentInvokeResponse

```json
{
  "output": "string",
  "thread_id": "string",
  "model": "string",
  "metadata": {
    "triage_level": "GREEN|AMBER|RED",
    "triage_reasons": ["string"],
    "fallback_used": boolean,
    "guardrail_sanitized": boolean,
    "sanitizer_reasons": ["string"],
    "request_id": "string"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `output` | string | AI generated response |
| `thread_id` | string | Conversation ID (echoed from request or generated) |
| `model` | string | Model name used (e.g., "gpt-4o-mini") |
| `metadata` | object | Additional processing information |

### AgentInvokeMetadata

| Field | Type | Description |
|-------|------|-------------|
| `triage_level` | string | Safety triage result: GREEN, AMBER, or RED |
| `triage_reasons` | array | List of reasons if AMBER/RED |
| `fallback_used` | boolean | True if model error occurred and fallback used |
| `guardrail_sanitized` | boolean | True if output was modified by sanitizer |
| `sanitizer_reasons` | array | List of sanitization reasons |
| `request_id` | string | Unique request identifier |
| `retrieval_used` | boolean | True when RAG context was attached to the answer |
| `retrieval_query` | string | Conversation-aware query sent to the retriever |
| `retrieval_query_rewritten` | boolean | True when an LLM rewrote the retrieval query before search |
| `retrieved_sources` | array | Retrieved chunk metadata used for grounding |

---

## Headers

All responses include these observability headers:

| Header | Description | Example |
|--------|-------------|---------|
| `X-Request-ID` | Unique request identifier | `550e8400-e29b-41d4-a716-446655440000` |
| `X-Latency-Ms` | Request processing time in milliseconds | `1250` |

---

## Safety Levels

### TriageLevel Enum

| Level | Color | Description | HTTP Status |
|-------|-------|-------------|-------------|
| `GREEN` | 🟢 | Normal conversation flow | 200 |
| `AMBER` | 🟡 | Proceed with caution, metadata included | 200 |
| `RED` | 🔴 | Request blocked | 400 |

### RED Triggers

Requests are blocked (RED) when containing:

1. **Emergency Combinations:**
   - chest pain + shortness of breath
   - one-sided weakness + slurred speech (stroke symptoms)

2. **Crisis Signals:**
   - suicide, kill myself, end my life
   - 자해, 죽고싶다 (Korean)

3. **Security Threats:**
   - ignore previous instructions
   - api key, password requests

### AMBER Triggers

Requests proceed (AMBER) with caution metadata:

- High fever for multiple days
- Severe abdominal pain
- Persistent vomiting
- Suspicious security language

---

## Error Handling

### Client Errors (4xx)

| Status | Cause | Resolution |
|--------|-------|------------|
| `400` | Safety triage blocked (RED) | Review request content |
| `422` | Validation error (invalid JSON/schema) | Check request format |

### Server Errors (5xx)

| Status | Cause | Resolution |
|--------|-------|------------|
| `500` | Model provider error | Fallback message returned automatically |
| `503` | Service not ready (missing API key) | Configure OPENAI_API_KEY |

---

## Examples

### Conversation Flow

```bash
# First message
curl -X POST http://localhost:8000/api/v1/agent/invoke \
  -H "Content-Type: application/json" \
  -d '{"message": "안녕하세요"}'

# Response: thread_id = "abc-123"

# Continue conversation
curl -X POST http://localhost:8000/api/v1/agent/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "message": "건강에 대해 조언해주세요",
    "thread_id": "abc-123"
  }'

# Same thread_id = context preserved
```

### Safety Block Example

```bash
curl -X POST http://localhost:8000/api/v1/agent/invoke \
  -H "Content-Type: application/json" \
  -d '{"message": "I have chest pain and shortness of breath"}'

# Response: 400 Bad Request
# {
#   "detail": {
#     "message": "Request blocked by safety triage",
#     "reasons": ["possible cardiopulmonary emergency"]
#   }
# }
```

---

## Rate Limits

Currently no explicit rate limiting is implemented.

**Recommendations:**
- Implement client-side rate limiting
- Monitor usage via CloudWatch (AWS)
- Consider API Gateway for production rate limiting
