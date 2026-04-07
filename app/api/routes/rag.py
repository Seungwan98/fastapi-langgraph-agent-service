from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status

from ...core.dependencies import get_agent_service
from ...core.settings import Settings, get_settings
from ...schemas.rag import RAGRebuildResponse
from ...services.agent_graph import AgentService
from ...services.retriever import build_rag_index_from_settings


router = APIRouter()


@router.post("/rebuild", response_model=RAGRebuildResponse, status_code=status.HTTP_200_OK)
def rebuild_rag_index(
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
    settings: Settings = Depends(get_settings),
    agent_service: AgentService = Depends(get_agent_service),
) -> RAGRebuildResponse:
    """큐레이션 문서로 RAG 인덱스를 재생성한다."""
    if not settings.rag_admin_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG admin rebuild is not configured",
        )
    if x_admin_token != settings.rag_admin_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token",
        )

    try:
        build_result = build_rag_index_from_settings(settings)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    agent_service.retriever.refresh_index()
    return RAGRebuildResponse(
        status="ok",
        document_count=build_result.document_count,
        chunk_count=build_result.chunk_count,
        output_path=build_result.output_path,
        embedding_model=build_result.embedding_model,
        chunk_size=build_result.chunk_size,
        chunk_overlap=build_result.chunk_overlap,
    )
