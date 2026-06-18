"""Session handling for authenticated agent requests."""

from datetime import datetime, timedelta, timezone

SESSION_TTL = timedelta(hours=12)


def is_session_valid(issued_at: datetime) -> bool:
    """Return True if the session has not expired."""
    return datetime.now(timezone.utc) - issued_at < SESSION_TTL
