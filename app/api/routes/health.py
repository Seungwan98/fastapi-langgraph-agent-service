from fastapi import APIRouter, Depends, HTTPException, status

from app.core.settings import Settings, get_settings


router = APIRouter()


@router.get("/live", summary="Liveness probe", status_code=status.HTTP_200_OK)
def live() -> dict[str, str]:
    """서비스가 살아 있는지 확인하는 응답을 반환한다."""
    return {"status": "ok"}


@router.get("/ready", summary="Readiness probe")
def ready(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    """필수 설정 기준으로 서비스 준비 상태를 확인한다."""
    if not settings.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY is not configured",
        )
    return {"status": "ready"}
