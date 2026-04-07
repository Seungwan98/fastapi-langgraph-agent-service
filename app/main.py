import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .api.routes.agent import router as agent_router
from .api.routes.health import router as health_router
from .api.routes.rag import router as rag_router
from .api.routes.threat_intel import router as threat_intel_router
from .core.settings import get_settings


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """FastAPI 애플리케이션을 생성하고 설정한다."""
    app = FastAPI(title="LangGraph Agent Service", version="0.1.0")
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_origin_regex=settings.backend_cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_request_context(request: Request, call_next):
        """요청 메타데이터와 응답 시간 헤더를 기록한다."""
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "request_id=%s method=%s path=%s status=%s latency_ms=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            latency_ms,
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Latency-Ms"] = str(latency_ms)
        return response

    app.include_router(health_router, prefix="/health", tags=["health"])
    app.include_router(agent_router, prefix="/api/v1/agent", tags=["agent"])
    app.include_router(rag_router, prefix="/api/v1/rag", tags=["rag"])
    app.include_router(threat_intel_router, prefix="/api/v1/threat-intel", tags=["threat-intel"])
    return app


app = create_app()
