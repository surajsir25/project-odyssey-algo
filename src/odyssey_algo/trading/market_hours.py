"""NSE market session helpers (IST)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)

# NSE holidays for 2026 (extend as needed).
NSE_HOLIDAYS_2026 = frozenset(
    {
        date(2026, 1, 26),
        date(2026, 3, 3),
        date(2026, 3, 26),
        date(2026, 4, 3),
        date(2026, 4, 14),
        date(2026, 5, 1),
        date(2026, 8, 15),
        date(2026, 10, 2),
        date(2026, 10, 20),
        date(2026, 11, 5),
        date(2026, 11, 24),
        date(2026, 12, 25),
    }
)


def now_ist() -> datetime:
    return datetime.now(IST)


def is_trading_day(day: date | None = None) -> bool:
    day = day or now_ist().date()
    return day.weekday() < 5 and day not in NSE_HOLIDAYS_2026


def is_market_open(at: datetime | None = None) -> bool:
    at = at or now_ist()
    if at.tzinfo is None:
        at = at.replace(tzinfo=IST)
    else:
        at = at.astimezone(IST)

    if not is_trading_day(at.date()):
        return False

    current = at.time()
    return MARKET_OPEN <= current <= MARKET_CLOSE


def seconds_until_market_open(at: datetime | None = None) -> int:
    at = at or now_ist()
    if at.tzinfo is None:
        at = at.replace(tzinfo=IST)
    else:
        at = at.astimezone(IST)

    if is_market_open(at):
        return 0

    candidate = datetime.combine(at.date(), MARKET_OPEN, tzinfo=IST)
    if at.time() > MARKET_CLOSE or not is_trading_day(at.date()):
        candidate = _next_trading_day_open(at)

    delta = candidate - at
    return max(0, int(delta.total_seconds()))


def _next_trading_day_open(at: datetime) -> datetime:
    day = at.date() + timedelta(days=1)
    while not is_trading_day(day):
        day += timedelta(days=1)
    return datetime.combine(day, MARKET_OPEN, tzinfo=IST)


def to_utc_iso(at: datetime) -> str:
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    return at.astimezone(timezone.utc).isoformat()
