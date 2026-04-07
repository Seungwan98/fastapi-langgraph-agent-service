from functools import lru_cache

from fastapi import Depends, HTTPException, status

from .settings import Settings, get_settings
from ..services.agent_graph import AgentService
from ..services.threat_intel_rag import ThreatIntelRAGService


@lru_cache(maxsize=4)
def _get_agent_service_instance(
    openai_api_key: str,
    openai_model: str,
    checkpoint_db_path: str,
    rag_enabled: bool,
    rag_index_path: str,
    rag_source_dir: str,
    rag_embedding_model: str,
    rag_top_k: int,
    rag_min_score: float,
    rag_chunk_size: int,
    rag_chunk_overlap: int,
    rag_history_turns: int,
    rag_query_rewrite_enabled: bool,
    rag_admin_token: str,
    public_medical_enabled: bool,
    public_medical_source_path: str,
    public_medical_base_url: str,
    public_medical_top_k: int,
    fhir_enabled: bool,
    fhir_source_path: str,
    fhir_base_url: str,
    fhir_bearer_token: str,
    fhir_observation_limit: int,
) -> AgentService:
    """주어진 설정으로 에이전트 서비스를 만들고 캐시한다."""
    service_settings = Settings(
        OPENAI_API_KEY=openai_api_key,
        OPENAI_MODEL=openai_model,
        CHECKPOINT_DB_PATH=checkpoint_db_path,
        RAG_ENABLED=rag_enabled,
        RAG_INDEX_PATH=rag_index_path,
        RAG_SOURCE_DIR=rag_source_dir,
        RAG_EMBEDDING_MODEL=rag_embedding_model,
        RAG_TOP_K=rag_top_k,
        RAG_MIN_SCORE=rag_min_score,
        RAG_CHUNK_SIZE=rag_chunk_size,
        RAG_CHUNK_OVERLAP=rag_chunk_overlap,
        RAG_HISTORY_TURNS=rag_history_turns,
        RAG_QUERY_REWRITE_ENABLED=rag_query_rewrite_enabled,
        RAG_ADMIN_TOKEN=rag_admin_token,
        PUBLIC_MEDICAL_ENABLED=public_medical_enabled,
        PUBLIC_MEDICAL_SOURCE_PATH=public_medical_source_path,
        PUBLIC_MEDICAL_BASE_URL=public_medical_base_url,
        PUBLIC_MEDICAL_TOP_K=public_medical_top_k,
        FHIR_ENABLED=fhir_enabled,
        FHIR_SOURCE_PATH=fhir_source_path,
        FHIR_BASE_URL=fhir_base_url,
        FHIR_BEARER_TOKEN=fhir_bearer_token,
        FHIR_OBSERVATION_LIMIT=fhir_observation_limit,
    )
    return AgentService(settings=service_settings)


def clear_agent_service_cache() -> None:
    """캐시된 에이전트 서비스 인스턴스를 비운다."""
    _get_agent_service_instance.cache_clear()


def get_agent_service(settings: Settings = Depends(get_settings)) -> AgentService:
    """사용 가능한 에이전트 서비스를 반환하고 설정이 없으면 예외를 발생시킨다."""
    if not settings.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY is not configured; set it and retry",
        )
    return _get_agent_service_instance(
        openai_api_key=settings.openai_api_key or "",
        openai_model=settings.openai_model,
        checkpoint_db_path=settings.checkpoint_db_path,
        rag_enabled=settings.rag_enabled,
        rag_index_path=settings.rag_index_path,
        rag_source_dir=settings.rag_source_dir,
        rag_embedding_model=settings.rag_embedding_model,
        rag_top_k=settings.rag_top_k,
        rag_min_score=settings.rag_min_score,
        rag_chunk_size=settings.rag_chunk_size,
        rag_chunk_overlap=settings.rag_chunk_overlap,
        rag_history_turns=settings.rag_history_turns,
        rag_query_rewrite_enabled=settings.rag_query_rewrite_enabled,
        rag_admin_token=settings.rag_admin_token or "",
        public_medical_enabled=settings.public_medical_enabled,
        public_medical_source_path=settings.public_medical_source_path,
        public_medical_base_url=settings.public_medical_base_url or "",
        public_medical_top_k=settings.public_medical_top_k,
        fhir_enabled=settings.fhir_enabled,
        fhir_source_path=settings.fhir_source_path,
        fhir_base_url=settings.fhir_base_url or "",
        fhir_bearer_token=settings.fhir_bearer_token or "",
        fhir_observation_limit=settings.fhir_observation_limit,
    )


@lru_cache(maxsize=4)
def _get_threat_intel_service_instance(
    parsed_dir: str,
    index_dir: str,
    vision_model: str,
    answer_model: str,
    embedding_model: str,
) -> ThreatIntelRAGService:
    """주어진 설정으로 threat-intel RAG 서비스를 만들고 캐시한다."""
    return ThreatIntelRAGService(
        parsed_dir=parsed_dir,
        index_dir=index_dir,
        vision_model=vision_model,
        answer_model=answer_model,
        embedding_model=embedding_model,
    )


def clear_threat_intel_service_cache() -> None:
    """캐시된 threat-intel 서비스 인스턴스를 비운다."""
    _get_threat_intel_service_instance.cache_clear()


def get_threat_intel_service(
    settings: Settings = Depends(get_settings),
) -> ThreatIntelRAGService:
    """설정 기반 threat-intel RAG 서비스를 반환한다."""
    return _get_threat_intel_service_instance(
        parsed_dir=settings.threat_intel_parsed_dir,
        index_dir=settings.threat_intel_index_dir,
        vision_model=settings.threat_intel_vision_model,
        answer_model=settings.threat_intel_answer_model,
        embedding_model=settings.threat_intel_embedding_model,
    )
