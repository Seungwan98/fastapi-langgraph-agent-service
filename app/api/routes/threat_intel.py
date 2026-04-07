from __future__ import annotations

import importlib
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status

from ...core.dependencies import get_threat_intel_service
from ...core.settings import Settings, get_settings
from ...schemas.threat_intel import (
    ThreatIntelIngestItem,
    ThreatIntelIngestResponse,
    ThreatIntelQueryRequest,
    ThreatIntelQueryResponse,
    ThreatIntelRetrievedSource,
)
from ...services.threat_intel_rag import ThreatIntelRAGService


router = APIRouter()


def _ensure_threat_intel_runtime_dependencies() -> None:
    """Threat-intel 파이프라인의 런타임 의존성이 있는지 검증한다."""
    required_modules = {
        "langchain_upstage": "langchain-upstage",
        "langchain_chroma": "langchain-chroma",
        "langchain_classic": "langchain-classic",
    }
    for module_name, package_name in required_modules.items():
        try:
            importlib.import_module(module_name)
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Threat intel runtime dependency missing: install `{package_name}`",
            ) from exc


def _ensure_threat_intel_query_runtime(settings: Settings) -> None:
    """Threat-intel query 파이프라인이 실제로 실행 가능한지 검증한다."""
    if not settings.threat_intel_is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Threat intel query requires OPENAI_API_KEY and UPSTAGE_API_KEY",
        )
    _ensure_threat_intel_runtime_dependencies()


def _ensure_threat_intel_ingest_runtime(settings: Settings) -> None:
    """Threat-intel ingest 파이프라인이 실제로 실행 가능한지 검증한다."""
    _ensure_threat_intel_query_runtime(settings)
    if not settings.threat_intel_admin_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Threat intel ingest is disabled until THREAT_INTEL_ADMIN_TOKEN is configured",
        )


@router.get("/ready", status_code=status.HTTP_200_OK)
def threat_intel_ready(
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """Threat-intel query 파이프라인이 실행 가능한지 확인한다."""
    _ensure_threat_intel_query_runtime(settings)
    return {"status": "ready"}


@router.get("/ingest-ready", status_code=status.HTTP_200_OK)
def threat_intel_ingest_ready(
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """Threat-intel ingest 파이프라인이 실행 가능한지 확인한다."""
    _ensure_threat_intel_ingest_runtime(settings)
    return {"status": "ready"}


@router.post("/ingest", response_model=ThreatIntelIngestResponse, status_code=status.HTTP_200_OK)
def ingest_threat_intel(
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
    settings: Settings = Depends(get_settings),
    threat_intel_service: ThreatIntelRAGService = Depends(get_threat_intel_service),
) -> ThreatIntelIngestResponse:
    """Configured local PDF 디렉터리를 파싱해 멀티모달 RAG 아티팩트를 생성한다."""
    _ensure_threat_intel_ingest_runtime(settings)
    if x_admin_token != settings.threat_intel_admin_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token",
        )

    try:
        results = threat_intel_service.ingest_directory(settings.threat_intel_local_pdf_dir)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ThreatIntelIngestResponse(
        status="ok",
        pdf_count=len(results),
        results=[ThreatIntelIngestItem.model_validate(result.__dict__) for result in results],
    )


@router.post("/query", response_model=ThreatIntelQueryResponse, status_code=status.HTTP_200_OK)
def query_threat_intel(
    payload: ThreatIntelQueryRequest,
    settings: Settings = Depends(get_settings),
    threat_intel_service: ThreatIntelRAGService = Depends(get_threat_intel_service),
) -> ThreatIntelQueryResponse:
    """파싱/인덱싱된 PDF 아티팩트를 하이브리드 검색 후 답변한다."""
    _ensure_threat_intel_query_runtime(settings)

    try:
        result = threat_intel_service.query(payload.question)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ThreatIntelQueryResponse(
        answer=str(result.get("answer", "")),
        retrieved_sources=[
            ThreatIntelRetrievedSource(
                doc_id=doc.metadata.get("doc_id"),
                doc_key=doc.metadata.get("doc_key"),
                page=doc.metadata.get("page"),
                source=doc.metadata.get("source"),
            )
            for doc in (result.get("retrieved_docs") or [])
        ],
    )
