from datetime import datetime, timezone

from langchain_core.tools import tool


@tool
def time_tool() -> str:
    """현재 UTC 시간을 ISO 형식으로 반환한다."""
    return datetime.now(timezone.utc).isoformat()
