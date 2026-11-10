from __future__ import annotations

import calendar
from datetime import datetime


def add_billing_interval(dt: datetime, interval: str) -> datetime:
    """Advance ``dt`` by one monthly or annual billing interval."""
    if interval == 'monthly':
        month = dt.month + 1
        year = dt.year
        if month > 12:
            month = 1
            year += 1
        day = min(dt.day, calendar.monthrange(year, month)[1])
        return dt.replace(year=year, month=month, day=day)

    year = dt.year + 1
    day = dt.day
    try:
        return dt.replace(year=year, day=day)
    except ValueError:
        # Feb 29 → Feb 28 on non-leap years
        return dt.replace(year=year, month=2, day=28)


def period_day_counts(*, period_start: datetime, period_end: datetime, now: datetime) -> tuple[int, int]:
    """Return (total_days, remaining_days) for proration (minimum 1 total day)."""
    total = max(1, (period_end.date() - period_start.date()).days)
    remaining = max(0, (period_end.date() - now.date()).days)
    remaining = min(remaining, total)
    return total, remaining
