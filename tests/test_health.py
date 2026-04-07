from fastapi.testclient import TestClient

from app.core.dependencies import clear_agent_service_cache
from app.core.settings import get_settings
from app.main import app


client = TestClient(app)


def reset_settings_cache():
    """헬스 체크 테스트 사이에 캐시를 비운다."""
    get_settings.cache_clear()
    clear_agent_service_cache()


def test_live_endpoint():
    """live 엔드포인트가 정상 응답과 헤더를 주는지 확인한다."""
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "X-Request-ID" in response.headers
    assert "X-Latency-Ms" in response.headers


def test_ready_without_api_key(monkeypatch):
    """API 키가 없을 때 ready 엔드포인트가 503을 주는지 확인한다."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    reset_settings_cache()

    response = client.get("/health/ready")
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]
    assert "X-Request-ID" in response.headers
    assert "X-Latency-Ms" in response.headers


def test_ready_with_api_key(monkeypatch):
    """API 키가 있을 때 ready 엔드포인트가 정상 응답하는지 확인한다."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    reset_settings_cache()

    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert "X-Request-ID" in response.headers
    assert "X-Latency-Ms" in response.headers
