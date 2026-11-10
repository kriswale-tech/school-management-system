"""Shared date-range parsing for every Messages data surface (v4.1 §2.18)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django.utils import timezone
from rest_framework.exceptions import ValidationError

RANGE_CHOICES = ('today', 'last_7', 'last_30', 'this_month', 'last_month', 'custom')
DEFAULT_RANGE = 'last_30'

# Legacy / shorthand aliases accepted from older UI clients.
RANGE_ALIASES = {
    '7d': 'last_7',
    '30d': 'last_30',
    'last7': 'last_7',
    'last30': 'last_30',
}


@dataclass(frozen=True)
class DateRange:
    key: str
    start: datetime
    end: datetime

    def as_dict(self) -> dict:
        return {
            'range': self.key,
            'from': self.start.isoformat(),
            'to': self.end.isoformat(),
        }


def _start_of_day(moment: datetime) -> datetime:
    return timezone.make_aware(
        datetime.combine(timezone.localtime(moment).date(), time.min),
        timezone.get_current_timezone(),
    )


def _parse_boundary(raw: str, *, field: str, end_of_day: bool) -> datetime:
    value = (raw or '').strip()
    if not value:
        raise ValidationError({field: 'A date or datetime is required for a custom range.'})
    try:
        parsed = datetime.fromisoformat(value)
        if len(value) == 10:
            parsed = datetime.combine(parsed.date(), time.max if end_of_day else time.min)
    except ValueError as exc:
        raise ValidationError({field: 'Use YYYY-MM-DD or an ISO 8601 datetime.'}) from exc
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def resolve_range(params, *, default: str = DEFAULT_RANGE) -> DateRange:
    """Resolve ``?range=`` (+ optional ``from``/``to``) into an inclusive window."""
    raw = (params.get('range') or default).strip() or default
    key = RANGE_ALIASES.get(raw, raw)
    if key not in RANGE_CHOICES:
        raise ValidationError({
            'range': f'Unsupported range. Choose one of: {", ".join(RANGE_CHOICES)}.',
        })

    now = timezone.now()
    today_start = _start_of_day(now)

    if key == 'custom':
        # Accept both ``from``/``to`` (canonical) and ``date_from``/``date_to``.
        start_raw = params.get('from') or params.get('date_from')
        end_raw = params.get('to') or params.get('date_to')
        start = _parse_boundary(start_raw, field='from', end_of_day=False)
        end = _parse_boundary(end_raw, field='to', end_of_day=True)
        if end < start:
            raise ValidationError({'to': 'End of range must not precede the start.'})
        return DateRange('custom', start, end)

    if key == 'today':
        return DateRange(key, today_start, now)
    if key == 'last_7':
        return DateRange(key, today_start - timedelta(days=6), now)
    if key == 'last_30':
        return DateRange(key, today_start - timedelta(days=29), now)

    local_today = timezone.localtime(now).date()
    if key == 'this_month':
        start = timezone.make_aware(
            datetime.combine(local_today.replace(day=1), time.min),
            timezone.get_current_timezone(),
        )
        return DateRange(key, start, now)

    # last_month
    first_of_this_month = local_today.replace(day=1)
    last_month_end_day = first_of_this_month - timedelta(days=1)
    start = timezone.make_aware(
        datetime.combine(last_month_end_day.replace(day=1), time.min),
        timezone.get_current_timezone(),
    )
    end = timezone.make_aware(
        datetime.combine(last_month_end_day, time.max),
        timezone.get_current_timezone(),
    )
    return DateRange(key, start, end)


def month_window(moment=None) -> tuple[datetime, datetime]:
    """Calendar-month window containing ``moment`` (defaults to now)."""
    now = moment or timezone.now()
    local_date = timezone.localtime(now).date()
    start = timezone.make_aware(
        datetime.combine(local_date.replace(day=1), time.min),
        timezone.get_current_timezone(),
    )
    if local_date.month == 12:
        next_first = local_date.replace(year=local_date.year + 1, month=1, day=1)
    else:
        next_first = local_date.replace(month=local_date.month + 1, day=1)
    end = timezone.make_aware(
        datetime.combine(next_first, time.min),
        timezone.get_current_timezone(),
    )
    return start, end


def day_window(moment=None) -> tuple[datetime, datetime]:
    """Calendar-day window containing ``moment`` (defaults to now)."""
    now = moment or timezone.now()
    start = _start_of_day(now)
    return start, start + timedelta(days=1)
