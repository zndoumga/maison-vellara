"""
Timezone-aware timestamp helpers.

Boutiques live in different timezones and only transact during opening hours.
We sample local wall-clock times within store hours, then convert to UTC for
storage (mirroring how a real POS records local time but a data platform
normalises to UTC).
"""
from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

# Hour-of-day weighting within opening hours — luxury footfall peaks late
# morning and mid-afternoon, with a lunch lull.
_HOUR_SHAPE = {
    10: 0.6, 11: 1.0, 12: 0.7, 13: 0.5, 14: 0.9,
    15: 1.1, 16: 1.2, 17: 1.0, 18: 0.8, 19: 0.6,
    20: 0.5, 21: 0.4,
}


def sample_local_time(
    rng: random.Random,
    open_hour: int,
    close_hour: int,
    window: tuple[int, int] | None = None,
) -> time:
    """
    Sample a local time within [open_hour, close_hour).

    If `window` (start_hour, end_hour) is given, the result is additionally
    constrained to that intra-day window (used in live mode so a run only
    produces events for the slice of the day that has 'happened').
    """
    lo, hi = open_hour, close_hour
    if window is not None:
        lo = max(lo, window[0])
        hi = min(hi, window[1])
    if hi <= lo:
        return time(open_hour, 0, 0)

    hours = list(range(lo, hi))
    weights = [_HOUR_SHAPE.get(h, 0.5) for h in hours]
    hour = rng.choices(hours, weights=weights, k=1)[0]
    minute = rng.randint(0, 59)
    second = rng.randint(0, 59)
    return time(hour, minute, second)


def local_to_utc(d: date, t: time, tz_name: str) -> datetime:
    """Combine a date + local time in tz_name and return a UTC datetime."""
    local_dt = datetime.combine(d, t, tzinfo=ZoneInfo(tz_name))
    return local_dt.astimezone(ZoneInfo("UTC"))


def utc_now_naive_iso(dt: datetime) -> str:
    """ISO-8601 string in UTC with a trailing Z."""
    return dt.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")


def daterange(start: date, end: date):
    """Inclusive day-by-day iterator from start to end."""
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)
