from datetime import datetime, timezone
from typing import Optional


def get_utc_now() -> datetime:
    """Returns the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def parse_iso_datetime(date_str: str) -> Optional[datetime]:
    """Parses an ISO format string into a datetime object."""
    try:
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None
