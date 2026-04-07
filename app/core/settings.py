from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    upstage_api_key: Optional[str] = Field(default=None, alias="UPSTAGE_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    checkpoint_db_path: str = Field(default="data/agent_checkpoints.sqlite", alias="CHECKPOINT_DB_PATH")
    backend_cors_origins_raw: str = Field(default="http://localhost:5173", alias="BACKEND_CORS_ORIGINS")
    backend_cors_origin_regex: Optional[str] = Field(default=None, alias="BACKEND_CORS_ORIGIN_REGEX")
    agent_fallback_message: str = Field(
        default="We could not process your request right now. Please try again shortly.",
        alias="AGENT_FALLBACK_MESSAGE",
    )
    rag_enabled: bool = Field(default=False, alias="RAG_ENABLED")
    rag_index_path: str = Field(default="data/rag_index.json", alias="RAG_INDEX_PATH")
    rag_source_dir: str = Field(default="docs/knowledge", alias="RAG_SOURCE_DIR")
    rag_embedding_model: str = Field(default="text-embedding-3-small", alias="RAG_EMBEDDING_MODEL")
    rag_top_k: int = Field(default=4, alias="RAG_TOP_K")
    rag_min_score: float = Field(default=0.2, alias="RAG_MIN_SCORE")
    rag_chunk_size: int = Field(default=800, alias="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(default=120, alias="RAG_CHUNK_OVERLAP")
    rag_history_turns: int = Field(default=3, alias="RAG_HISTORY_TURNS")
    rag_query_rewrite_enabled: bool = Field(default=False, alias="RAG_QUERY_REWRITE_ENABLED")
    rag_admin_token: Optional[str] = Field(default=None, alias="RAG_ADMIN_TOKEN")
    public_medical_enabled: bool = Field(default=False, alias="PUBLIC_MEDICAL_ENABLED")
    public_medical_source_path: str = Field(default="data/public_medical_reference.json", alias="PUBLIC_MEDICAL_SOURCE_PATH")
    public_medical_base_url: Optional[str] = Field(default=None, alias="PUBLIC_MEDICAL_BASE_URL")
    public_medical_top_k: int = Field(default=2, alias="PUBLIC_MEDICAL_TOP_K")
    fhir_enabled: bool = Field(default=False, alias="FHIR_ENABLED")
    fhir_source_path: str = Field(default="data/fhir_patient_context.json", alias="FHIR_SOURCE_PATH")
    fhir_base_url: Optional[str] = Field(default=None, alias="FHIR_BASE_URL")
    fhir_bearer_token: Optional[str] = Field(default=None, alias="FHIR_BEARER_TOKEN")
    fhir_observation_limit: int = Field(default=5, alias="FHIR_OBSERVATION_LIMIT")
    threat_intel_local_pdf_dir: str = Field(default="data/threat_intel/raw/pdfs", alias="THREAT_INTEL_LOCAL_PDF_DIR")
    threat_intel_parsed_dir: str = Field(default="data/threat_intel/parsed", alias="THREAT_INTEL_PARSED_DIR")
    threat_intel_index_dir: str = Field(default="data/threat_intel/index", alias="THREAT_INTEL_INDEX_DIR")
    threat_intel_vision_model: str = Field(default="gpt-4o-mini", alias="THREAT_INTEL_VISION_MODEL")
    threat_intel_answer_model: str = Field(default="gpt-4o-mini", alias="THREAT_INTEL_ANSWER_MODEL")
    threat_intel_embedding_model: str = Field(default="solar-embedding-1-large", alias="THREAT_INTEL_EMBEDDING_MODEL")
    threat_intel_admin_token: Optional[str] = Field(default=None, alias="THREAT_INTEL_ADMIN_TOKEN")

    @property
    def is_ready(self) -> bool:
        """최소 실행 설정이 준비되었는지 확인한다."""
        return bool(self.openai_api_key and self.openai_api_key.strip())


    @property
    def threat_intel_is_ready(self) -> bool:
        """멀티모달 PDF RAG 실행에 필요한 핵심 키가 준비되었는지 확인한다."""
        return bool(
            self.openai_api_key
            and self.openai_api_key.strip()
            and self.upstage_api_key
            and self.upstage_api_key.strip()
        )

    @property
    def backend_cors_origins(self) -> list[str]:
        """설정된 CORS 출처 문자열을 목록으로 정리한다."""
        return [origin.strip() for origin in self.backend_cors_origins_raw.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """환경 변수에서 읽은 설정 객체를 캐시해서 반환한다."""
    return Settings()
