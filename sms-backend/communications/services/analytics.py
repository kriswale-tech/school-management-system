"""School usage matrix and individual school reports (v4.1 §2.12).

SMS consumption is always reported in billable segments, never in message or
recipient counts: a 2-segment message to 3 guardians is 6 units.
"""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce

from billing.models import SchoolSubscription, TopUpPurchase
from communications.models import CreditAccount, CreditLedgerEntry
from communications.services.aggregates import (
    EMAIL,
    SMS,
    classification_breakdown,
    comms_cash_from_schools,
    delivery_status_counts,
    delivery_usage_metrics,
    guardian_deliveries,
    ledger_unit_metrics,
    provider_accepted_statuses,
    school_balances,
)
from communications.services.ranges import DateRange
from schools.models import School

_ZERO = Decimal('0')
_MONEY = DecimalField(max_digits=18, decimal_places=6)


def _unit(value) -> str:
    return str(Decimal(value or 0).quantize(Decimal('0.000001')))


def _money(value) -> str:
    return str(Decimal(value or 0).quantize(Decimal('0.01')))


def _usage_rows(*, date_range: DateRange, channel: str, classification: str | None = None):
    """Per-school aggregates for one channel, in one query."""
    from notifications.models import GuardianDelivery

    qs = GuardianDelivery.objects.filter(
        channel=channel,
        created_at__gte=date_range.start,
        created_at__lte=date_range.end,
        status__in=provider_accepted_statuses(),
    )
    if classification:
        qs = qs.filter(billing_classification=classification)

    unit_sum = (
        Sum('segments') if channel == SMS else Count('id')
    )
    paid_filter = Q(billing_classification=GuardianDelivery.BillingClassification.PAID)
    free_filter = Q(billing_classification=GuardianDelivery.BillingClassification.FREE)
    sponsored_filter = Q(
        billing_classification=GuardianDelivery.BillingClassification.SPONSORED,
    )

    if channel == SMS:
        annotations = {
            'total_units': Coalesce(unit_sum, Value(0)),
            'paid_units': Coalesce(Sum('segments', filter=paid_filter), Value(0)),
            'free_units': Coalesce(Sum('segments', filter=free_filter), Value(0)),
            'sponsored_units': Coalesce(Sum('segments', filter=sponsored_filter), Value(0)),
        }
    else:
        annotations = {
            'total_units': Coalesce(unit_sum, Value(0)),
            'paid_units': Coalesce(Count('id', filter=paid_filter), Value(0)),
            'free_units': Coalesce(Count('id', filter=free_filter), Value(0)),
            'sponsored_units': Coalesce(Count('id', filter=sponsored_filter), Value(0)),
        }

    annotations.update(
        {
            'messages': Count('id'),
            'provider_cost_ghs': Coalesce(
                Sum('provider_cost_snapshot_ghs'),
                Value(_ZERO, _MONEY),
            ),
            'free_sponsored_cost_ghs': Coalesce(
                Sum(
                    'provider_cost_snapshot_ghs',
                    filter=free_filter | sponsored_filter,
                ),
                Value(_ZERO, _MONEY),
            ),
            'usage_valued_revenue_ghs': Coalesce(
                Sum('school_unit_price_snapshot_ghs', filter=paid_filter),
                Value(_ZERO, _MONEY),
            ),
            'credits_charged': Coalesce(Sum('credits_charged'), Value(0)),
            'credits_refunded': Coalesce(Sum('credits_refunded'), Value(0)),
            'unpriced_rows': Count('id', filter=Q(provider_cost_snapshot_ghs__isnull=True)),
            'unbilled_rows': Count('id', filter=Q(unbilled=True)),
        },
    )

    return {
        str(row['school_id']): row
        for row in qs.values('school_id').annotate(**annotations)
    }


def _balance_map() -> dict:
    out: dict[str, dict] = {}
    for row in CreditAccount.objects.values('school_id', 'channel', 'balance'):
        out.setdefault(str(row['school_id']), {})[row['channel']] = int(row['balance'] or 0)
    return out


def _addon_map() -> dict:
    out = {}
    for subscription in SchoolSubscription.objects.filter(is_current=True).select_related(
        'sms_sku',
        'email_sku',
    ):
        out[str(subscription.school_id)] = {
            'subscription_status': subscription.status,
            'interval': subscription.interval,
            'sms_addon_enabled': bool(subscription.sms_addon_enabled),
            'email_addon_enabled': bool(subscription.email_addon_enabled),
            'sms_sku_code': subscription.sms_sku.code if subscription.sms_sku_id else None,
            'email_sku_code': subscription.email_sku.code if subscription.email_sku_id else None,
        }
    return out


def school_usage_matrix(
    *,
    date_range: DateRange,
    channel: str | None = None,
    classification: str | None = None,
    search: str = '',
    addon_status: str = '',
):
    """Searchable per-school usage matrix. Returns a list of plain dicts."""
    schools = School.objects.all().order_by('name')
    if search:
        schools = schools.filter(name__icontains=search)

    sms_rows = _usage_rows(
        date_range=date_range,
        channel=SMS,
        classification=classification,
    ) if channel in (None, '', SMS) else {}
    email_rows = _usage_rows(
        date_range=date_range,
        channel=EMAIL,
        classification=classification,
    ) if channel in (None, '', EMAIL) else {}
    balances = _balance_map()
    addons = _addon_map()

    results = []
    for school in schools:
        key = str(school.pk)
        addon = addons.get(key, {})
        if addon_status == 'enabled' and not (
            addon.get('sms_addon_enabled') or addon.get('email_addon_enabled')
        ):
            continue
        if addon_status == 'disabled' and (
            addon.get('sms_addon_enabled') or addon.get('email_addon_enabled')
        ):
            continue

        sms = sms_rows.get(key, {})
        email = email_rows.get(key, {})
        school_balance = balances.get(key, {})
        provider_cost = Decimal(sms.get('provider_cost_ghs') or 0) + Decimal(
            email.get('provider_cost_ghs') or 0,
        )
        revenue = Decimal(sms.get('usage_valued_revenue_ghs') or 0) + Decimal(
            email.get('usage_valued_revenue_ghs') or 0,
        )
        free_expense = Decimal(sms.get('free_sponsored_cost_ghs') or 0) + Decimal(
            email.get('free_sponsored_cost_ghs') or 0,
        )

        results.append(
            {
                'school_id': key,
                'school_name': school.name,
                'school_status': getattr(school, 'status', ''),
                'sms': {
                    'messages': int(sms.get('messages') or 0),
                    'segments_consumed': int(sms.get('total_units') or 0),
                    'paid_segments': int(sms.get('paid_units') or 0),
                    'free_segments': int(sms.get('free_units') or 0),
                    'sponsored_segments': int(sms.get('sponsored_units') or 0),
                    'balance_units': school_balance.get(SMS, 0),
                    'unpriced_rows': int(sms.get('unpriced_rows') or 0),
                    'unbilled_rows': int(sms.get('unbilled_rows') or 0),
                },
                'email': {
                    'messages': int(email.get('messages') or 0),
                    'emails_consumed': int(email.get('total_units') or 0),
                    'paid_emails': int(email.get('paid_units') or 0),
                    'free_emails': int(email.get('free_units') or 0),
                    'sponsored_emails': int(email.get('sponsored_units') or 0),
                    'balance_units': school_balance.get(EMAIL, 0),
                    'unpriced_rows': int(email.get('unpriced_rows') or 0),
                    'unbilled_rows': int(email.get('unbilled_rows') or 0),
                },
                'economics': {
                    'provider_cost_ghs': _unit(provider_cost),
                    'usage_valued_revenue_ghs': _unit(revenue),
                    'free_sponsored_expense_ghs': _unit(free_expense),
                    'gross_profit_contribution_ghs': _unit(
                        revenue - provider_cost - free_expense,
                    ),
                    'email_provider_cost_is_estimated': True,
                },
                'addons': addon,
            },
        )
    return results


def _topup_history(*, school, start, end):
    return [
        {
            'id': str(row.pk),
            'channel': row.channel,
            'credits': row.credits,
            'amount_ghs': _money(row.amount_ghs),
            'status': row.status,
            'created_at': row.created_at,
            'package': row.package.code if row.package_id else None,
        }
        for row in TopUpPurchase.objects.filter(
            school=school,
            created_at__gte=start,
            created_at__lte=end,
        ).select_related('package').order_by('-created_at')[:200]
    ]


def _ledger_history(*, school, start, end, channel: str | None = None):
    qs = CreditLedgerEntry.objects.filter(
        school=school,
        occurred_at__gte=start,
        occurred_at__lte=end,
    )
    if channel:
        qs = qs.filter(channel=channel)
    return [
        {
            'id': str(row.pk),
            'channel': row.channel,
            'entry_type': row.entry_type,
            'delta': row.delta,
            'balance_after': row.balance_after,
            'occurred_at': row.occurred_at,
            'idempotency_key': row.idempotency_key,
            'metadata': row.metadata,
        }
        for row in qs.order_by('-occurred_at')[:500]
    ]


def school_report(*, school, date_range: DateRange, channel: str | None = None) -> dict:
    """Individual school messaging report (v4.1 §2.12)."""
    start, end = date_range.start, date_range.end
    channels = [channel] if channel in (SMS, EMAIL) else [SMS, EMAIL]
    balances = school_balances(school=school)

    per_channel = {}
    for key in channels:
        accepted = guardian_deliveries(
            start=start,
            end=end,
            channel=key,
            school=school,
        )
        everything = guardian_deliveries(
            start=start,
            end=end,
            channel=key,
            school=school,
            accepted_only=False,
        )
        usage = delivery_usage_metrics(accepted, channel=key)
        split = classification_breakdown(start=start, end=end, channel=key, school=school)
        ledger = ledger_unit_metrics(start=start, end=end, channel=key, school=school)
        per_channel[key] = {
            'channel': key,
            'balance_units': balances.get(key, 0),
            'usage': {
                'messages': usage['messages'],
                'units_consumed': usage['units'],
                'segments_consumed': usage['segments'],
                'credits_charged': usage['credits_charged'],
                'credits_refunded': usage['credits_refunded'],
                'provider_cost_ghs': _unit(usage['provider_cost_ghs']),
                'usage_valued_revenue_ghs': _unit(
                    split['paid']['usage_valued_revenue_ghs'],
                ),
                'unpriced_rows': usage['unpriced_rows'],
                'unbilled_rows': usage['unbilled_rows'],
                'provider_cost_is_estimated': key == EMAIL,
            },
            'classification': {
                name: {
                    'messages': value['messages'],
                    'units': value['units'],
                    'provider_cost_ghs': _unit(value['provider_cost_ghs']),
                }
                for name, value in split.items()
            },
            'delivery_statuses': delivery_status_counts(everything),
            'credits': ledger,
            'unit_note': (
                'SMS consumption is reported in billable segments, never in '
                'message or recipient counts.'
            )
            if key == SMS
            else '1 email credit = 1 provider-accepted recipient delivery attempt.',
        }

    cash = comms_cash_from_schools(start=start, end=end, school=school)

    return {
        'school': {
            'id': str(school.pk),
            'name': school.name,
            'status': getattr(school, 'status', ''),
        },
        'range': date_range.as_dict(),
        'channels': per_channel,
        'layer_3_cash_from_school': {
            'topup_cash_ghs': _money(cash['topup_cash_ghs']),
            'addon_cash_ghs': _money(cash['addon_cash_ghs']),
            'total_cash_ghs': _money(cash['total_cash_ghs']),
        },
        'addons': _addon_map().get(str(school.pk), {}),
        'topup_history': _topup_history(school=school, start=start, end=end),
        'ledger': _ledger_history(school=school, start=start, end=end, channel=channel),
        'trend': consumption_trend(school=school, date_range=date_range, channel=channel),
    }


def consumption_trend(*, school=None, date_range: DateRange, channel: str | None = None):
    """Daily consumed units over the window, for charting."""
    from django.db.models.functions import TruncDate

    from notifications.models import GuardianDelivery

    qs = GuardianDelivery.objects.filter(
        created_at__gte=date_range.start,
        created_at__lte=date_range.end,
        status__in=provider_accepted_statuses(),
    )
    if school is not None:
        qs = qs.filter(school=school)
    if channel in (SMS, EMAIL):
        qs = qs.filter(channel=channel)

    rows = (
        qs.annotate(day=TruncDate('created_at'))
        .values('day', 'channel')
        .annotate(
            messages=Count('id'),
            segments=Coalesce(Sum('segments'), Value(0)),
        )
        .order_by('day')
    )
    out: dict[str, dict] = {}
    for row in rows:
        day = row['day'].isoformat() if row['day'] else ''
        bucket = out.setdefault(day, {'date': day, 'sms_segments': 0, 'emails': 0})
        if row['channel'] == SMS:
            bucket['sms_segments'] += int(row['segments'] or 0)
        else:
            bucket['emails'] += int(row['messages'] or 0)
    return list(out.values())
