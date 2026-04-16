from __future__ import annotations

from typing import Optional

from fastapi.testclient import TestClient

from app.core.dependencies import clear_agent_service_cache, get_agent_service
from app.core.settings import get_settings
from app.main import app
from app.services.errors import ModelProviderError


client = TestClient(app)


class FakeAgentService:
    def __init__(
        self,
        output: str = "ok",
        *,
        raise_error: bool = False,
        model: str = "fake-model",
        retrieval_used: bool = False,
        retrieval_query: str = "",
        retrieval_query_rewritten: bool = False,
        retrieved_sources: Optional[list[dict[str, object]]] = None,
    ):
        """API 테스트용 가짜 에이전트 응답을 설정한다."""
        self.output = output
        self.raise_error = raise_error
        self.model = model
        self.retrieval_used = retrieval_used
        self.retrieval_query = retrieval_query
        self.retrieval_query_rewritten = retrieval_query_rewritten
        self.retrieved_sources = retrieved_sources or []
        self.last_patient_id: Optional[str] = None

    def invoke(self, message: str, thread_id: Optional[str] = None, patient_id: Optional[str] = None) -> dict[str, object]:
        """가짜 결과를 반환하거나 테스트용 오류를 발생시킨다."""
        self.last_patient_id = patient_id
        if self.raise_error:
            raise ModelProviderError("provider failed", thread_id=thread_id or "tid", model=self.model)
        return {
            "output": self.output,
            "thread_id": thread_id or "tid",
            "model": self.model,
            "retrieval_used": self.retrieval_used,
            "retrieval_query": self.retrieval_query,
            "retrieval_query_rewritten": self.retrieval_query_rewritten,
            "retrieved_sources": self.retrieved_sources,
        }


def reset_settings_cache():
    """테스트 사이에 설정과 에이전트 캐시를 비운다."""
    get_settings.cache_clear()
    clear_agent_service_cache()


def test_agent_invoke_requires_api_key(monkeypatch):
    """API 키가 없을 때 503을 반환하는지 확인한다."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    reset_settings_cache()
    app.dependency_overrides[get_agent_service] = lambda: FakeAgentService("no-call")

    response = client.post("/api/v1/agent/invoke", json={"message": "hi"})
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]

    app.dependency_overrides = {}


def test_agent_invoke_success(monkeypatch):
    """정상 호출 시 GREEN 메타데이터와 응답을 반환하는지 확인한다."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    reset_settings_cache()
    app.dependency_overrides[get_agent_service] = lambda: FakeAgentService("pong")

    response = client.post("/api/v1/agent/invoke", json={"message": "ping", "thread_id": "custom-thread"})
    assert response.status_code == 200
    data = response.json()
    assert data["output"] == "pong"
    assert data["thread_id"] == "custom-thread"
    assert data["model"] == "fake-model"
    assert data["metadata"]["triage_level"] == "GREEN"
    assert data["metadata"]["fallback_used"] is False
    assert data["metadata"]["retrieval_used"] is False
    assert data["metadata"]["retrieval_query"] == ""
    assert data["metadata"]["retrieval_query_rewritten"] is False
    assert data["metadata"]["retrieved_sources"] == []

    app.dependency_overrides = {}


def test_agent_invoke_includes_retrieval_metadata(monkeypatch):
    """검색 결과 메타데이터가 API 응답에 포함되는지 확인한다."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    reset_settings_cache()
    app.dependency_overrides[get_agent_service] = lambda: FakeAgentService(
        "grounded answer",
        retrieval_used=True,
        retrieval_query="headache for two weeks\nwhat should I ask my doctor",
        retrieval_query_rewritten=True,
        retrieved_sources=[
            {
                "chunk_id": "faq-chunk-1",
                    "source": "knowledge-base/faq.md",
                "title": "FAQ",
                "score": 0.91,
                "source_kind": "knowledge",
                "provider": "local_rag",
            }
        ],
    )

    response = client.post("/api/v1/agent/invoke", json={"message": "What should I ask a doctor?"})
    assert response.status_code == 200
    metadata = response.json()["metadata"]
    assert metadata["retrieval_used"] is True
    assert metadata["retrieval_query"] == "headache for two weeks\nwhat should I ask my doctor"
    assert metadata["retrieval_query_rewritten"] is True
    assert metadata["retrieved_sources"][0]["chunk_id"] == "faq-chunk-1"
    assert metadata["retrieved_sources"][0]["score"] == 0.91
    assert metadata["retrieved_sources"][0]["source_kind"] == "knowledge"
    assert metadata["retrieved_sources"][0]["provider"] == "local_rag"

    app.dependency_overrides = {}


def test_agent_invoke_passes_patient_id_to_service(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    reset_settings_cache()
    fake_service = FakeAgentService("patient-aware")
    app.dependency_overrides[get_agent_service] = lambda: fake_service

    response = client.post(
        "/api/v1/agent/invoke",
        json={"message": "review my recent vitals", "patient_id": "demo-patient"},
    )

    assert response.status_code == 200
    assert fake_service.last_patient_id == "demo-patient"

    app.dependency_overrides = {}


def test_agent_red_triage_block(monkeypatch):
    """RED triage 요청이 에이전트 실행 전에 차단되는지 확인한다."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    reset_settings_cache()
    app.dependency_overrides[get_agent_service] = lambda: FakeAgentService("should-not-run")

    response = client.post(
        "/api/v1/agent/invoke",
        json={"message": "I have chest pain and shortness of breath right now. Am I dying?"},
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "blocked" in detail["message"]
    assert any("emergency" in reason for reason in detail["reasons"])

    app.dependency_overrides = {}


def test_agent_red_triage_block_for_standalone_respiratory_distress(monkeypatch):
    """숨이 안 쉬어진다는 단독 표현도 RED로 차단되는지 확인한다."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    reset_settings_cache()
    app.dependency_overrides[get_agent_service] = lambda: FakeAgentService("should-not-run")

    response = client.post(
        "/api/v1/agent/invoke",
        json={"message": "I can't breathe right now"},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "blocked" in detail["message"]
    assert any("respiratory" in reason for reason in detail["reasons"])

    app.dependency_overrides = {}


def test_agent_amber_metadata(monkeypatch):
    """AMBER triage 사유가 메타데이터에 담기는지 확인한다."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    reset_settings_cache()
    app.dependency_overrides[get_agent_service] = lambda: FakeAgentService("ok")

    response = client.post("/api/v1/agent/invoke", json={"message": "I have had high fever for 3 days"})
    assert response.status_code == 200
    meta = response.json()["metadata"]
    assert meta["triage_level"] == "AMBER"
    assert any("persistent fever" in reason for reason in meta["triage_reasons"])

    app.dependency_overrides = {}


def test_agent_fallback_on_provider_error(monkeypatch):
    """프로바이더 오류 시 폴백 메시지를 반환하는지 확인한다."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_FALLBACK_MESSAGE", "fallback-response")
    reset_settings_cache()
    app.dependency_overrides[get_agent_service] = lambda: FakeAgentService("none", raise_error=True)

    response = client.post("/api/v1/agent/invoke", json={"message": "ping", "thread_id": "tid-123"})
    assert response.status_code == 200
    data = response.json()
    assert data["output"] == "fallback-response"
    assert data["thread_id"] == "tid-123"
    assert data["metadata"]["fallback_used"] is True
    assert data["metadata"]["retrieval_used"] is False
    assert data["metadata"]["retrieval_query"] == ""
    assert data["metadata"]["retrieval_query_rewritten"] is False
    assert data["metadata"]["retrieved_sources"] == []

    app.dependency_overrides = {}


def test_agent_sanitizer_metadata(monkeypatch):
    """출력 마스킹 여부가 메타데이터에 표시되는지 확인한다."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    reset_settings_cache()
    app.dependency_overrides[get_agent_service] = lambda: FakeAgentService("api key: sk-SECRETKEY")

    response = client.post("/api/v1/agent/invoke", json={"message": "hello"})
    assert response.status_code == 200
    data = response.json()
    assert data["output"].endswith("[REDACTED]")
    assert data["metadata"]["guardrail_sanitized"] is True
    assert data["metadata"]["sanitizer_reasons"]

    app.dependency_overrides = {}
