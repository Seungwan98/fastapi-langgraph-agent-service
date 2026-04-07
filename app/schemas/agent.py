from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class AgentInvokeRequest(BaseModel):
    message: str = Field(..., description="User message for the agent")
    thread_id: Optional[str] = Field(None, description="Identifier for LangGraph checkpointing")
    patient_id: Optional[str] = Field(None, description="Optional patient identifier for FHIR-backed context")


class RetrievedSource(BaseModel):
    chunk_id: str
    source: str
    title: Optional[str] = None
    score: Optional[float] = None
    type: Optional[str] = None
    severity: Optional[str] = None
    intent: Optional[str] = None
    source_kind: Optional[str] = None
    provider: Optional[str] = None
    url: Optional[str] = None
    patient_id: Optional[str] = None


class AgentInvokeMetadata(BaseModel):
    triage_level: Optional[str] = None
    triage_reasons: Optional[List[str]] = None
    guardrail_sanitized: Optional[bool] = None
    sanitizer_reasons: Optional[List[str]] = None
    fallback_used: Optional[bool] = None
    request_id: Optional[str] = None
    retrieval_used: Optional[bool] = None
    retrieval_query: Optional[str] = None
    retrieval_query_rewritten: Optional[bool] = None
    retrieved_sources: Optional[List[RetrievedSource]] = None


class AgentInvokeResponse(BaseModel):
    output: str
    thread_id: str
    model: str
    metadata: Optional[AgentInvokeMetadata] = None
