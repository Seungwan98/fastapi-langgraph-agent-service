"""Standardized API error response middleware."""

from fastapi import Request
from fastapi.responses import JSONResponse


async def error_envelope(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error": str(exc)})
