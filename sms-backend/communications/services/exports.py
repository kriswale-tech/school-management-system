"""CSV / XLSX exports for every Messages dataset (v4.1 §2.19).

Uses the existing ``shared.services.spreadsheets`` writers (openpyxl is already
a project dependency), so exports match the format used elsewhere in the app.
Export generation is audited by the view layer.
"""

from __future__ import annotations

from decimal import Decimal

from rest_framework.exceptions import ValidationError

from communications.models import (
    CreditLedgerEntry,
    EmailPricingConfig,
    ProviderExpense,
    ProviderPurchase,
    ProviderReconciliationItem,
    SmsEncodingConfig,
)
from communications.services.aggregates import EMAIL, SMS, classification_breakdown
from communications.services.analytics import school_usage_matrix
from communications.services.profitability import messaging_profitability
from communications.services.ranges import DateRange
from shared.services.spreadsheets import build_csv_bytes, build_xlsx_bytes

FORMATS = ('csv', 'xlsx')

EXPORT_TYPES = (
    'school_usage',
    'provider_purchases',
    'provider_expenses',
    'sms_pricing_history',
    'email_pricing_history',
    'profitability',
    'free_sponsored',
    'credit_ledger',
    'monthly_summary',
    'reconciliation',
)


def _iso(value) -> str:
    return value.isoformat() if value else ''


def _decimal(value) -> str:
    return str(Decimal(value)) if value is not None else ''


def _school_usage(date_range: DateRange, params) -> tuple[list[str], list[dict]]:
    rows = school_usage_matrix(
        date_range=date_range,
        channel=(params.get('channel') or '') or None,
        classification=(params.get('classification') or '') or None,
        search=(params.get('q') or '').strip(),
        addon_status=(params.get('addon_status') or '').strip(),
    )
    headers = [
        'school_id',
        'school_name',
        'school_status',
        'sms_messages',
        'sms_segments_consumed',
        'sms_paid_segments',
        'sms_free_segments',
        'sms_sponsored_segments',
        'sms_balance_units',
        'email_messages',
        'emails_consumed',
        'paid_emails',
        'free_emails',
        'sponsored_emails',
        'email_balance_units',
        'provider_cost_ghs',
        'usage_valued_revenue_ghs',
        'free_sponsored_expense_ghs',
        'gross_profit_contribution_ghs',
        'sms_addon_enabled',
        'email_addon_enabled',
        'unpriced_rows',
        'unbilled_rows',
    ]
    flat = [
        {
            'school_id': row['school_id'],
            'school_name': row['school_name'],
            'school_status': row['school_status'],
            'sms_messages': row['sms']['messages'],
            'sms_segments_consumed': row['sms']['segments_consumed'],
            'sms_paid_segments': row['sms']['paid_segments'],
            'sms_free_segments': row['sms']['free_segments'],
            'sms_sponsored_segments': row['sms']['sponsored_segments'],
            'sms_balance_units': row['sms']['balance_units'],
            'email_messages': row['email']['messages'],
            'emails_consumed': row['email']['emails_consumed'],
            'paid_emails': row['email']['paid_emails'],
            'free_emails': row['email']['free_emails'],
            'sponsored_emails': row['email']['sponsored_emails'],
            'email_balance_units': row['email']['balance_units'],
            'provider_cost_ghs': row['economics']['provider_cost_ghs'],
            'usage_valued_revenue_ghs': row['economics']['usage_valued_revenue_ghs'],
            'free_sponsored_expense_ghs': row['economics']['free_sponsored_expense_ghs'],
            'gross_profit_contribution_ghs': (
                row['economics']['gross_profit_contribution_ghs']
            ),
            'sms_addon_enabled': row['addons'].get('sms_addon_enabled', ''),
            'email_addon_enabled': row['addons'].get('email_addon_enabled', ''),
            'unpriced_rows': row['sms']['unpriced_rows'] + row['email']['unpriced_rows'],
            'unbilled_rows': row['sms']['unbilled_rows'] + row['email']['unbilled_rows'],
        }
        for row in rows
    ]
    return headers, flat


def _provider_purchases(date_range: DateRange, params) -> tuple[list[str], list[dict]]:
    qs = ProviderPurchase.objects.filter(
        purchased_at__gte=date_range.start,
        purchased_at__lte=date_range.end,
    ).select_related('recorded_by')
    provider = (params.get('provider') or '').strip()
    if provider:
        qs = qs.filter(provider=provider)
    headers = [
        'purchased_at',
        'provider',
        'channel',
        'amount_ghs',
        'credits_or_units',
        'effective_cost_per_unit_ghs',
        'provider_reference',
        'payment_method',
        'recorded_by',
        'notes',
    ]
    rows = [
        {
            'purchased_at': _iso(row.purchased_at),
            'provider': row.provider,
            'channel': row.channel,
            'amount_ghs': _decimal(row.amount_ghs),
            'credits_or_units': row.credits_or_units,
            'effective_cost_per_unit_ghs': _decimal(row.effective_cost_per_unit),
            'provider_reference': row.provider_reference,
            'payment_method': row.payment_method,
            'recorded_by': getattr(row.recorded_by, 'email', ''),
            'notes': row.notes,
        }
        for row in qs
    ]
    return headers, rows


def _provider_expenses(date_range: DateRange, params) -> tuple[list[str], list[dict]]:
    qs = ProviderExpense.objects.filter(
        period_start__lte=date_range.end,
        period_end__gte=date_range.start,
    ).select_related('recorded_by')
    provider = (params.get('provider') or '').strip()
    if provider:
        qs = qs.filter(provider=provider)
    headers = [
        'period_start',
        'period_end',
        'provider',
        'channel',
        'expense_kind',
        'amount_ghs',
        'units',
        'provider_reference',
        'source',
        'recorded_by',
        'notes',
    ]
    rows = [
        {
            'period_start': _iso(row.period_start),
            'period_end': _iso(row.period_end),
            'provider': row.provider,
            'channel': row.channel,
            'expense_kind': row.expense_kind,
            'amount_ghs': _decimal(row.amount_ghs),
            'units': row.units if row.units is not None else '',
            'provider_reference': row.provider_reference,
            'source': row.source,
            'recorded_by': getattr(row.recorded_by, 'email', ''),
            'notes': row.notes,
        }
        for row in qs
    ]
    return headers, rows


def _sms_pricing_history(date_range: DateRange, params) -> tuple[list[str], list[dict]]:
    qs = SmsEncodingConfig.objects.select_related('changed_by').order_by(
        'encoding',
        '-effective_from',
    )
    headers = [
        'encoding',
        'effective_from',
        'effective_to',
        'is_active',
        'provider_cost_per_segment_ghs',
        'school_price_per_segment_ghs',
        'single_segment_limit',
        'multipart_segment_limit',
        'changed_by',
        'notes',
    ]
    rows = [
        {
            'encoding': row.encoding,
            'effective_from': _iso(row.effective_from),
            'effective_to': _iso(row.effective_to),
            'is_active': row.is_active,
            'provider_cost_per_segment_ghs': _decimal(row.provider_cost_per_segment_ghs),
            'school_price_per_segment_ghs': _decimal(row.school_price_per_segment_ghs),
            'single_segment_limit': row.single_segment_limit,
            'multipart_segment_limit': row.multipart_segment_limit,
            'changed_by': getattr(row.changed_by, 'email', ''),
            'notes': row.notes,
        }
        for row in qs
    ]
    return headers, rows


def _email_pricing_history(date_range: DateRange, params) -> tuple[list[str], list[dict]]:
    qs = EmailPricingConfig.objects.select_related('changed_by').order_by('-effective_from')
    headers = [
        'effective_from',
        'effective_to',
        'is_active',
        'school_price_per_credit_ghs',
        'estimated_provider_cost_per_email_ghs',
        'provider_cost_is_estimated',
        'billing_unit',
        'changed_by',
        'notes',
    ]
    rows = [
        {
            'effective_from': _iso(row.effective_from),
            'effective_to': _iso(row.effective_to),
            'is_active': row.is_active,
            'school_price_per_credit_ghs': _decimal(row.school_price_per_credit_ghs),
            'estimated_provider_cost_per_email_ghs': _decimal(
                row.estimated_provider_cost_per_email_ghs,
            ),
            'provider_cost_is_estimated': True,
            'billing_unit': row.billing_unit,
            'changed_by': getattr(row.changed_by, 'email', ''),
            'notes': row.notes,
        }
        for row in qs
    ]
    return headers, rows


def _profitability(date_range: DateRange, params) -> tuple[list[str], list[dict]]:
    report = messaging_profitability(date_range=date_range)
    headers = [
        'channel',
        'view',
        'metric',
        'value',
        'is_estimated',
    ]
    rows: list[dict] = []
    for channel, block in report['channels'].items():
        for view_name in ('cash_view', 'usage_view', 'credits_view'):
            for metric, value in block.get(view_name, {}).items():
                if metric in ('note', 'unpriced_note'):
                    continue
                rows.append(
                    {
                        'channel': channel,
                        'view': view_name.replace('_view', ''),
                        'metric': metric,
                        'value': value,
                        'is_estimated': channel == EMAIL and 'cost' in metric,
                    },
                )
    for view_name, block in report['combined'].items():
        for metric, value in block.items():
            rows.append(
                {
                    'channel': 'combined',
                    'view': view_name.replace('_view', ''),
                    'metric': metric,
                    'value': value,
                    'is_estimated': 'cost' in metric,
                },
            )
    return headers, rows


def _free_sponsored(date_range: DateRange, params) -> tuple[list[str], list[dict]]:
    headers = [
        'channel',
        'classification',
        'messages',
        'units',
        'provider_cost_ghs',
        'provider_cost_is_estimated',
    ]
    rows = []
    for channel in (SMS, EMAIL):
        split = classification_breakdown(
            start=date_range.start,
            end=date_range.end,
            channel=channel,
        )
        for classification in ('free', 'sponsored'):
            metrics = split[classification]
            rows.append(
                {
                    'channel': channel,
                    'classification': classification,
                    'messages': metrics['messages'],
                    'units': metrics['units'],
                    'provider_cost_ghs': _decimal(metrics['provider_cost_ghs']),
                    'provider_cost_is_estimated': channel == EMAIL,
                },
            )
    return headers, rows


def _credit_ledger(date_range: DateRange, params) -> tuple[list[str], list[dict]]:
    qs = CreditLedgerEntry.objects.filter(
        occurred_at__gte=date_range.start,
        occurred_at__lte=date_range.end,
    ).select_related('school', 'actor_platform_user')
    school_id = (params.get('school') or '').strip()
    if school_id:
        qs = qs.filter(school_id=school_id)
    channel = (params.get('channel') or '').strip()
    if channel:
        qs = qs.filter(channel=channel)
    headers = [
        'occurred_at',
        'school_id',
        'school_name',
        'channel',
        'entry_type',
        'delta',
        'balance_after',
        'idempotency_key',
        'actor',
    ]
    rows = [
        {
            'occurred_at': _iso(row.occurred_at),
            'school_id': str(row.school_id),
            'school_name': row.school.name if row.school_id else '',
            'channel': row.channel,
            'entry_type': row.entry_type,
            'delta': row.delta,
            'balance_after': row.balance_after,
            'idempotency_key': row.idempotency_key,
            'actor': getattr(row.actor_platform_user, 'email', ''),
        }
        for row in qs.order_by('-occurred_at')[:50000]
    ]
    return headers, rows


def _monthly_summary(date_range: DateRange, params) -> tuple[list[str], list[dict]]:
    from django.db.models import Count, Sum, Value
    from django.db.models.functions import Coalesce, TruncMonth

    from communications.services.aggregates import provider_accepted_statuses
    from notifications.models import GuardianDelivery

    qs = (
        GuardianDelivery.objects.filter(
            created_at__gte=date_range.start,
            created_at__lte=date_range.end,
            status__in=provider_accepted_statuses(),
        )
        .annotate(month=TruncMonth('created_at'))
        .values('month', 'channel', 'billing_classification')
        .annotate(
            messages=Count('id'),
            segments=Coalesce(Sum('segments'), Value(0)),
            provider_cost_ghs=Coalesce(Sum('provider_cost_snapshot_ghs'), Value(Decimal('0'))),
            sell_value_ghs=Coalesce(
                Sum('school_unit_price_snapshot_ghs'),
                Value(Decimal('0')),
            ),
        )
        .order_by('month', 'channel', 'billing_classification')
    )
    headers = [
        'month',
        'channel',
        'billing_classification',
        'messages',
        'units',
        'provider_cost_ghs',
        'usage_valued_revenue_ghs',
        'provider_cost_is_estimated',
    ]
    rows = []
    for row in qs:
        units = int(row['segments'] or 0) if row['channel'] == SMS else int(row['messages'] or 0)
        rows.append(
            {
                'month': row['month'].date().isoformat() if row['month'] else '',
                'channel': row['channel'],
                'billing_classification': row['billing_classification'],
                'messages': int(row['messages'] or 0),
                'units': units,
                'provider_cost_ghs': _decimal(row['provider_cost_ghs']),
                'usage_valued_revenue_ghs': _decimal(row['sell_value_ghs']),
                'provider_cost_is_estimated': row['channel'] == EMAIL,
            },
        )
    return headers, rows


def _reconciliation(date_range: DateRange, params) -> tuple[list[str], list[dict]]:
    qs = ProviderReconciliationItem.objects.filter(
        created_at__gte=date_range.start,
        created_at__lte=date_range.end,
    ).select_related('run', 'school', 'resolved_by', 'ledger_entry')
    headers = [
        'created_at',
        'run_id',
        'provider',
        'channel',
        'school_id',
        'school_name',
        'discrepancy_type',
        'internal_delivery_type',
        'internal_delivery_id',
        'provider_message_id',
        'internal_value',
        'provider_value',
        'resolution',
        'resolution_note',
        'resolved_by',
        'resolved_at',
        'ledger_entry_delta',
        'detail',
    ]
    rows = [
        {
            'created_at': _iso(row.created_at),
            'run_id': str(row.run_id) if row.run_id else '',
            'provider': row.provider,
            'channel': row.channel,
            'school_id': str(row.school_id) if row.school_id else '',
            'school_name': row.school.name if row.school_id else '',
            'discrepancy_type': row.discrepancy_type,
            'internal_delivery_type': row.internal_delivery_type,
            'internal_delivery_id': row.internal_delivery_id,
            'provider_message_id': row.provider_message_id,
            'internal_value': row.internal_value,
            'provider_value': row.provider_value,
            'resolution': row.resolution,
            'resolution_note': row.resolution_note,
            'resolved_by': getattr(row.resolved_by, 'email', ''),
            'resolved_at': _iso(row.resolved_at),
            'ledger_entry_delta': (
                row.ledger_entry.delta if row.ledger_entry_id else ''
            ),
            'detail': row.detail,
        }
        for row in qs.order_by('-created_at')[:50000]
    ]
    return headers, rows


BUILDERS = {
    'school_usage': _school_usage,
    'provider_purchases': _provider_purchases,
    'provider_expenses': _provider_expenses,
    'sms_pricing_history': _sms_pricing_history,
    'email_pricing_history': _email_pricing_history,
    'profitability': _profitability,
    'free_sponsored': _free_sponsored,
    'credit_ledger': _credit_ledger,
    'monthly_summary': _monthly_summary,
    'reconciliation': _reconciliation,
}


def build_export(*, export_type: str, fmt: str, date_range: DateRange, params) -> dict:
    """Return ``{filename, content_type, body}`` for one export request."""
    if export_type not in BUILDERS:
        raise ValidationError({
            'type': f'Unsupported export type. Choose one of: {", ".join(EXPORT_TYPES)}.',
        })
    if fmt not in FORMATS:
        raise ValidationError({'format': 'Supported formats are csv and xlsx.'})

    headers, rows = BUILDERS[export_type](date_range, params)
    stamp = date_range.start.date().isoformat()
    filename = f'messages-{export_type}-{stamp}.{fmt}'

    if fmt == 'csv':
        return {
            'filename': filename,
            'content_type': 'text/csv; charset=utf-8',
            'body': build_csv_bytes(headers=headers, rows=_stringify(rows)),
        }
    return {
        'filename': filename,
        'content_type': (
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ),
        'body': build_xlsx_bytes(
            sheet_name=export_type[:31],
            headers=headers,
            rows=_stringify(rows),
        ),
    }


def _stringify(rows: list[dict]) -> list[dict]:
    """Booleans and ``None`` render inconsistently across writers — normalise."""
    out = []
    for row in rows:
        clean = {}
        for key, value in row.items():
            if value is None:
                clean[key] = ''
            elif isinstance(value, bool):
                clean[key] = 'yes' if value else 'no'
            else:
                clean[key] = value
        out.append(clean)
    return out
