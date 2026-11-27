from datetime import date, datetime, timezone
from functools import lru_cache
from typing import Optional
from zoneinfo import ZoneInfo

from core.config import settings


def utc_now() -> datetime:
    """Current instant (UTC). Single clock seam: tests patch this, never the system clock."""
    return datetime.now(timezone.utc)


@lru_cache
def _zone(name: str) -> ZoneInfo:
    return ZoneInfo(name)


def business_today(now: Optional[datetime] = None) -> date:
    """Calendar date in BUSINESS_TIMEZONE (not the server's or UTC date)."""
    return (now or utc_now()).astimezone(_zone(settings.BUSINESS_TIMEZONE)).date()
