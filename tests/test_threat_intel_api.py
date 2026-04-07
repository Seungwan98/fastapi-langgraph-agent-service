from __future__ import annotations

import importlib

from fastapi.testclient import TestClient

from app.core.dependencies import clear_threat_intel_service_cache, get_threat_intel_service
from app.core.settings import get_settings
from app.main import app
from app.services.threat_intel_rag import ThreatIntelIngestResult


client = TestClient(app)


class FakeThreatIntelService:
    def __init__(self, *, ingest_error: Exception | None = None, query_error: Exception | None = None):
        self.ingest_error = ingest_error
        self.query_error = query_error

    def ingest_directory(self, pdf_dir: str):
        if self.ingest_error:
            raise self.ingest_error
        return [
            ThreatIntelIngestResult(
                pdf_path=f"{pdf_dir}/sample.pdf",
                doc_key="sample-doc",
                artifact_dir="data/threat_intel/parsed/sample-doc",
                page_count=5,
                element_count=2,
                visual_summary_count=1,
                parent_count=5,
            )
        ]

    def query(self, question: str):
        if self.query_error:
            raise self.query_error
        class _Doc:
            metadata = {"doc_id": "sample-doc-page-1", "doc_key": "sample-doc", "page": 1, "source": "sample.pdf"}
        return {"answer": f"answer::{question}", "retrieved_docs": [_Doc()]}


def allow_runtime_dependency_checks(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.threat_intel.importlib.import_module",
        lambda name: object(),
    )


def reset_settings_cache() -> None:
    get_settings.cache_clear()
    clear_threat_intel_service_cache()


def test_threat_intel_ingest_requires_both_api_keys(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("UPSTAGE_API_KEY", "")
    reset_settings_cache()
    app.dependency_overrides[get_threat_intel_service] = lambda: FakeThreatIntelService()

    response = client.post("/api/v1/threat-intel/ingest")

    assert response.status_code == 503
    assert "UPSTAGE_API_KEY" in response.json()["detail"]
    app.dependency_overrides = {}


def test_threat_intel_ready_requires_both_api_keys(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("UPSTAGE_API_KEY", "")
    reset_settings_cache()

    response = client.get("/api/v1/threat-intel/ready")

    assert response.status_code == 503
    assert "UPSTAGE_API_KEY" in response.json()["detail"]


def test_threat_intel_ingest_ready_requires_admin_token(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("UPSTAGE_API_KEY", "test-upstage")
    monkeypatch.delenv("THREAT_INTEL_ADMIN_TOKEN", raising=False)
    reset_settings_cache()
    allow_runtime_dependency_checks(monkeypatch)

    response = client.get("/api/v1/threat-intel/ingest-ready")

    assert response.status_code == 503
    assert "THREAT_INTEL_ADMIN_TOKEN" in response.json()["detail"]


def test_threat_intel_ready_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("UPSTAGE_API_KEY", "test-upstage")
    reset_settings_cache()
    allow_runtime_dependency_checks(monkeypatch)

    response = client.get("/api/v1/threat-intel/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_threat_intel_ready_reports_missing_runtime_dependency(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("UPSTAGE_API_KEY", "test-upstage")
    monkeypatch.setenv("THREAT_INTEL_ADMIN_TOKEN", "secret-token")
    reset_settings_cache()

    real_import_module = importlib.import_module

    def fake_import_module(name: str):
        if name == "langchain_upstage":
            raise ImportError("missing")
        return real_import_module(name)

    monkeypatch.setattr("app.api.routes.threat_intel.importlib.import_module", fake_import_module)

    response = client.get("/api/v1/threat-intel/ready")

    assert response.status_code == 503
    assert "langchain-upstage" in response.json()["detail"]


def test_threat_intel_ingest_ready_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("UPSTAGE_API_KEY", "test-upstage")
    monkeypatch.setenv("THREAT_INTEL_ADMIN_TOKEN", "secret-token")
    reset_settings_cache()
    allow_runtime_dependency_checks(monkeypatch)

    response = client.get("/api/v1/threat-intel/ingest-ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_threat_intel_ingest_rejects_invalid_admin_token(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("UPSTAGE_API_KEY", "test-upstage")
    monkeypatch.setenv("THREAT_INTEL_ADMIN_TOKEN", "secret-token")
    reset_settings_cache()
    allow_runtime_dependency_checks(monkeypatch)
    app.dependency_overrides[get_threat_intel_service] = lambda: FakeThreatIntelService()

    response = client.post("/api/v1/threat-intel/ingest", headers={"X-Admin-Token": "wrong-token"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid admin token"
    app.dependency_overrides = {}


def test_threat_intel_ingest_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("UPSTAGE_API_KEY", "test-upstage")
    monkeypatch.setenv("THREAT_INTEL_ADMIN_TOKEN", "secret-token")
    monkeypatch.setenv("THREAT_INTEL_LOCAL_PDF_DIR", "data/threat_intel/raw/pdfs")
    reset_settings_cache()
    allow_runtime_dependency_checks(monkeypatch)
    app.dependency_overrides[get_threat_intel_service] = lambda: FakeThreatIntelService()

    response = client.post("/api/v1/threat-intel/ingest", headers={"X-Admin-Token": "secret-token"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["pdf_count"] == 1
    assert data["results"][0]["doc_key"] == "sample-doc"
    app.dependency_overrides = {}


def test_threat_intel_ingest_disabled_without_admin_token(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("UPSTAGE_API_KEY", "test-upstage")
    monkeypatch.delenv("THREAT_INTEL_ADMIN_TOKEN", raising=False)
    reset_settings_cache()
    allow_runtime_dependency_checks(monkeypatch)
    app.dependency_overrides[get_threat_intel_service] = lambda: FakeThreatIntelService()

    response = client.post("/api/v1/threat-intel/ingest")

    assert response.status_code == 503
    assert "THREAT_INTEL_ADMIN_TOKEN" in response.json()["detail"]
    app.dependency_overrides = {}


def test_threat_intel_query_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("UPSTAGE_API_KEY", "test-upstage")
    reset_settings_cache()
    allow_runtime_dependency_checks(monkeypatch)
    app.dependency_overrides[get_threat_intel_service] = lambda: FakeThreatIntelService()

    response = client.post("/api/v1/threat-intel/query", json={"question": "What keeps health anxiety going?"})

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "answer::What keeps health anxiety going?"
    assert data["retrieved_sources"][0]["doc_id"] == "sample-doc-page-1"
    app.dependency_overrides = {}


def test_threat_intel_query_maps_missing_artifacts_to_400(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("UPSTAGE_API_KEY", "test-upstage")
    reset_settings_cache()
    allow_runtime_dependency_checks(monkeypatch)
    app.dependency_overrides[get_threat_intel_service] = lambda: FakeThreatIntelService(
        query_error=ValueError("No parsed threat-intel artifacts found. Run the ingest script before querying.")
    )

    response = client.post("/api/v1/threat-intel/query", json={"question": "hello"})

    assert response.status_code == 400
    assert "Run the ingest script" in response.json()["detail"]
    app.dependency_overrides = {}
