from __future__ import annotations

from pydantic import BaseModel, Field


class ThreatIntelIngestItem(BaseModel):
    doc_key: str
    pdf_path: str
    artifact_dir: str
    page_count: int
    element_count: int
    visual_summary_count: int
    parent_count: int


class ThreatIntelIngestResponse(BaseModel):
    status: str
    pdf_count: int
    results: list[ThreatIntelIngestItem]


class ThreatIntelQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Question to ask over the indexed PDFs")


class ThreatIntelRetrievedSource(BaseModel):
    doc_id: str | None = None
    doc_key: str | None = None
    page: int | None = None
    source: str | None = None


class ThreatIntelQueryResponse(BaseModel):
    answer: str
    retrieved_sources: list[ThreatIntelRetrievedSource]
