from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.dependencies import clear_agent_service_cache, get_agent_service
from app.core.settings import get_settings
from app.main import app
from app.services.retriever import RAGBuildResult


client = TestClient(app)


class FakeRetriever:
    def __init__(self):
        self.refreshed = False

    def refresh_index(self) -> None:
        self.refreshed = True


class FakeAgentService:
    def __init__(self):
        self.retriever = FakeRetriever()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
    clear_agent_service_cache()


def test_rag_rebuild_requires_admin_token(monkeypatch):
    """관리자 토큰이 없으면 재빌드를 비활성화 상태로 거절하는지 확인한다."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("RAG_ADMIN_TOKEN", raising=False)
    reset_settings_cache()
    app.dependency_overrides[get_agent_service] = lambda: FakeAgentService()

    response = client.post("/api/v1/rag/rebuild")

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]

    app.dependency_overrides = {}


def test_rag_rebuild_rejects_invalid_token(monkeypatch):
    """잘못된 관리자 토큰이면 403을 반환하는지 확인한다."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("RAG_ADMIN_TOKEN", "secret-token")
    reset_settings_cache()
    app.dependency_overrides[get_agent_service] = lambda: FakeAgentService()

    response = client.post("/api/v1/rag/rebuild", headers={"X-Admin-Token": "wrong-token"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid admin token"

    app.dependency_overrides = {}


def test_rag_rebuild_success_refreshes_retriever(monkeypatch):
    """정상 재빌드가 성공 응답과 캐시 초기화를 수행하는지 확인한다."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("RAG_ADMIN_TOKEN", "secret-token")
    reset_settings_cache()
    fake_service = FakeAgentService()
    app.dependency_overrides[get_agent_service] = lambda: fake_service

    def fake_build(settings):
        assert settings.rag_admin_token == "secret-token"
        return RAGBuildResult(
            document_count=3,
            chunk_count=8,
            output_path="data/rag_index.json",
            embedding_model="text-embedding-3-small",
            chunk_size=800,
            chunk_overlap=120,
        )

    monkeypatch.setattr("app.api.routes.rag.build_rag_index_from_settings", fake_build)

    response = client.post("/api/v1/rag/rebuild", headers={"X-Admin-Token": "secret-token"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["document_count"] == 3
    assert data["chunk_count"] == 8
    assert fake_service.retriever.refreshed is True

    app.dependency_overrides = {}
