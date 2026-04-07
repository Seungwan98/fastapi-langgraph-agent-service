from fastapi import APIRouter, Depends, HTTPException, Request, status

from ...core.dependencies import get_agent_service
from ...core.settings import Settings, get_settings
from ...schemas.agent import AgentInvokeMetadata, AgentInvokeRequest, AgentInvokeResponse, RetrievedSource
from ...services.agent_graph import AgentService
from ...services.errors import ModelProviderError
from ...services.safety import TriageLevel, sanitize_output, triage_message


router = APIRouter()


@router.post("/invoke", response_model=AgentInvokeResponse)
def invoke_agent(
    payload: AgentInvokeRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    agent_service: AgentService = Depends(get_agent_service),
) -> AgentInvokeResponse:
    """에이전트 요청을 분류하고 폴백, 검색 메타데이터, 출력 정제를 포함해 처리한다."""
    if not settings.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY is not configured; set it and retry",
        )

    triage_decision = triage_message(payload.message)
    metadata = AgentInvokeMetadata(
        triage_level=triage_decision.level.value,
        triage_reasons=triage_decision.reasons,
    )

    if triage_decision.level is TriageLevel.RED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Request blocked by safety triage",
                "reasons": triage_decision.reasons,
            },
        )

    fallback_used = False
    try:
        result = agent_service.invoke(
            message=payload.message,
            thread_id=payload.thread_id,
            patient_id=payload.patient_id,
        )
    except ModelProviderError as exc:
        fallback_used = True
        thread_id = exc.thread_id or payload.thread_id or "fallback-thread"
        result = {
            "output": settings.agent_fallback_message,
            "thread_id": thread_id,
            "model": exc.model or settings.openai_model,
            "retrieval_used": False,
            "retrieval_query": "",
            "retrieval_query_rewritten": False,
            "retrieved_sources": [],
        }

    sanitized_output, sanitized, sanitizer_reasons = sanitize_output(result["output"])
    metadata.guardrail_sanitized = sanitized
    metadata.sanitizer_reasons = sanitizer_reasons
    metadata.fallback_used = fallback_used
    metadata.request_id = getattr(request.state, "request_id", None)
    metadata.retrieval_used = bool(result.get("retrieval_used", False))
    metadata.retrieval_query = str(result.get("retrieval_query", ""))
    metadata.retrieval_query_rewritten = bool(result.get("retrieval_query_rewritten", False))
    metadata.retrieved_sources = [
        RetrievedSource.model_validate(source) for source in (result.get("retrieved_sources") or [])
    ]

    return AgentInvokeResponse(
        output=sanitized_output,
        thread_id=result["thread_id"],
        model=result["model"],
        metadata=metadata,
    )
