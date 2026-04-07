# Code Conventions

## Overview

Coding standards and style guidelines for the FastAPI LangGraph Agent Service project.

## Python Style Guide

### PEP 8 Compliance

- **Line length**: 88 characters (Black formatter default)
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Double quotes for strings
- **Imports**: Sorted with isort (stdlib, third-party, local)

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| **Classes** | PascalCase | `AgentService`, `TriageDecision` |
| **Functions** | snake_case | `triage_message()`, `sanitize_output()` |
| **Variables** | snake_case | `thread_id`, `fallback_used` |
| **Constants** | UPPER_SNAKE_CASE | `_SECURITY_RED_PATTERNS` |
| **Private** | _leading_underscore | `_build_checkpointer()` |
| **Modules** | lowercase | `safety.py`, `agent_graph.py` |

### Type Hints

Always use type hints for function signatures:

```python
# ✅ Good
def triage_message(message: str) -> TriageDecision:
    ...

def invoke(self, message: str, thread_id: str | None = None) -> dict[str, str]:
    ...

# ❌ Bad
def triage_message(message):  # Missing types
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def triage_message(message: str) -> TriageDecision:
    """Analyze message for safety triage.
    
    Args:
        message: User input message to analyze.
        
    Returns:
        TriageDecision with level (RED/AMBER/GREEN) and reasons.
        
    Example:
        >>> decision = triage_message("chest pain")
        >>> decision.level
        TriageLevel.RED
    """
```

---

## Project Structure

### Directory Organization

```
app/
├── __init__.py
├── main.py                 # App factory, entry point
├── api/                    # API layer
│   ├── __init__.py
│   └── routes/
│       ├── __init__.py
│       ├── health.py       # Health endpoints
│       └── agent.py        # Agent endpoints
├── core/                   # Core utilities
│   ├── __init__.py
│   ├── settings.py         # Configuration
│   └── dependencies.py     # FastAPI dependencies
├── schemas/                # Pydantic models
│   ├── __init__.py
│   └── agent.py
└── services/               # Business logic
    ├── __init__.py
    ├── agent_graph.py      # LangGraph service
    ├── safety.py           # Safety/triage
    ├── tools.py            # Agent tools
    └── errors.py           # Custom exceptions
```

### Import Order

```python
# 1. Standard library
import re
import sqlite3
from pathlib import Path

# 2. Third-party packages
from fastapi import APIRouter, Depends
from langchain.agents import create_agent

# 3. Local modules
from ..core.settings import Settings
from .errors import ModelProviderError
```

---

## FastAPI Patterns

### Router Definition

```python
# app/api/routes/agent.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/invoke", response_model=AgentInvokeResponse)
def invoke_agent(payload: AgentInvokeRequest) -> AgentInvokeResponse:
    ...
```

### Dependency Injection

```python
# ✅ Good: Use Depends for injectable dependencies
@router.post("/invoke")
def invoke_agent(
    payload: AgentInvokeRequest,
    settings: Settings = Depends(get_settings),
    agent_service: AgentService = Depends(get_agent_service),
) -> AgentInvokeResponse:
    ...

# ✅ Good: Singleton pattern with lru_cache
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### Error Handling

```python
# ✅ Good: Custom exceptions with proper HTTP status
class ModelProviderError(Exception):
    def __init__(self, message: str, thread_id: str, model: str):
        super().__init__(message)
        self.thread_id = thread_id
        self.model = model

# In endpoint
try:
    result = agent_service.invoke(...)
except ModelProviderError as exc:
    # Return fallback, don't crash
    return AgentInvokeResponse(
        output=settings.agent_fallback_message,
        ...
    )
```

---

## Safety Code Patterns

### Triage Decision

```python
# ✅ Good: Use enum for type safety
class TriageLevel(str, Enum):
    RED = "RED"
    AMBER = "AMBER"
    GREEN = "GREEN"

@dataclass
class TriageDecision:
    level: TriageLevel
    reasons: list[str]
```

### Pattern Matching

```python
# ✅ Good: Compiled patterns with comments
# Emergency combinations: chest pain + SOB
triage_decision = triage_message(user_input)

if triage_decision.level is TriageLevel.RED:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "message": "Request blocked by safety triage",
            "reasons": triage_decision.reasons,
        },
    )
```

---

## Configuration

### Settings Management

```python
# app/core/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    
    @property
    def is_ready(self) -> bool:
        return bool(self.openai_api_key)
```

### Environment Variables

```bash
# .env - Never commit this file!
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

---

## Testing

### Test Structure

```python
# tests/test_agent_api.py
def test_agent_invoke_success(monkeypatch):
    # Arrange
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    reset_settings_cache()
    
    # Act
    response = client.post("/api/v1/agent/invoke", json={"message": "hi"})
    
    # Assert
    assert response.status_code == 200
    assert response.json()["metadata"]["triage_level"] == "GREEN"
```

### Mocking External Services

```python
class FakeAgentService:
    def invoke(self, message: str, thread_id: str | None = None):
        return {"output": "test", "thread_id": "tid", "model": "test-model"}

# In test
app.dependency_overrides[get_agent_service] = lambda: FakeAgentService()
```

---

## Git Conventions

### Commit Messages

```
type(scope): subject

body (optional)

footer (optional)
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting (no code change)
- `refactor`: Code restructuring
- `test`: Tests
- `chore`: Maintenance

**Examples:**
```
feat(safety): add allergic reaction triage rule

fix(agent): handle ModelProviderError gracefully

docs(readme): update deployment instructions
```

### Branch Naming

```
feature/add-postgres-support
fix/sanitize-null-bytes
hotfix/security-patch
docs/api-examples
```

---

## Documentation

### Code Comments

```python
# ❌ Don't: Obvious comments
x = x + 1  # Increment x

# ✅ Do: Explain why, not what
# Compensate for 1-based indexing in external API
x = x + 1
```

### README Updates

When adding features:
1. Update relevant section in README.md
2. Add to ARCHITECTURE.md if architectural
3. Update API.md if new endpoints
4. Update DEPLOYMENT.md if deployment changes

---

## Docker Conventions

### Dockerfile

```dockerfile
# Use specific version
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies first (cache optimization)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . .

# Run with gunicorn for production
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker"]
```

### .dockerignore

```
__pycache__
*.pyc
*.pyo
.git
.env
.venv
*.sqlite
data/
```

---

## Security Best Practices

1. **Never commit secrets**: Use .env, add to .gitignore
2. **Sanitize outputs**: Always run sanitize_output() on AI responses
3. **Validate inputs**: Use Pydantic models for request validation
4. **Limit exposure**: Security groups restrict SSH to My IP
5. **Dependency updates**: Regularly update requirements.txt

---

## Code Review Checklist

- [ ] Type hints present
- [ ] Docstrings for public functions
- [ ] Error handling appropriate
- [ ] No hardcoded secrets
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Security considerations addressed
