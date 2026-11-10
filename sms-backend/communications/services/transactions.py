"""Unified messaging transaction feed (v4.1 §2.19 "Transaction history coverage").

Covers Arkesel purchases, Resend expenses, school top-ups, SMS/email deductions,
free and sponsored sends, refunds/reversals, promotional allocations, manual
adjustments, pricing changes, and reconciliation resolutions.

Every row carries: date, type, amount or credit quantity, reference, related
school, provider, and the responsible administrator.
"""

from __future__ import annotations

from decimal import Decimal

from billing.models import Payment
from communications.models import (
    CreditLedgerEntry,
    EmailPricingConfig,
    ProviderExpense,
    ProviderPurchase,
    ProviderReconciliationItem,
    SmsEncodingConfig,
)

TYPE_CHOICES = (
    'provider_purchase',
    'provider_expense',
    'school_topup_payment',
    'credit_allocation',
    'credit_topup',
    'credit_promo_grant',
    'credit_usage_debit',
    'credit_reversal',
    'credit_manual_adjust',
    'free_send',
    'sponsored_send',
    'sms_pricing_change',
    'email_pricing_change',
    'reconciliation_resolution',
)

LEDGER_TYPE_MAP = {
    CreditLedgerEntry.EntryType.ALLOCATION_RECURRING: 'credit_allocation',
    CreditLedgerEntry.EntryType.TOPUP: 'credit_topup',
    CreditLedgerEntry.EntryType.PROMO_GRANT: 'credit_promo_grant',
    CreditLedgerEntry.EntryType.USAGE_DEBIT: 'credit_usage_debit',
    CreditLedgerEntry.EntryType.REVERSAL: 'credit_reversal',
    CreditLedgerEntry.EntryType.MANUAL_ADJUST: 'credit_manual_adjust',
}


def _row(
    *,
    occurred_at,
    kind: str,
    layer: str,
    description: str,
    amount_ghs=None,
    credits=None,
    reference: str = '',
    school_id=None,
    school_name: str = '',
    provider: str = '',
    channel: str = '',
    administrator: str = '',
    detail: dict | None = None,
) -> dict:
    return {
        'occurred_at': occurred_at,
        'type': kind,
        'layer': layer,
        'description': description,
        'amount_ghs': str(Decimal(amount_ghs).quantize(Decimal('0.01')))
        if amount_ghs is not None
        else None,
        'credits': credits,
        'reference': reference,
        'school_id': str(school_id) if school_id else None,
        'school_name': school_name,
        'provider': provider,
        'channel': channel,
        'administrator': administrator,
        'detail': detail or {},
    }


def _actor_label(user) -> str:
    if user is None:
        return ''
    return getattr(user, 'email', '') or str(user.pk)


def _provider_purchases(*, start, end, provider='', school_id=None):
    if school_id:
        return []
    qs = ProviderPurchase.objects.filter(purchased_at__gte=start, purchased_at__lte=end)
    if provider:
        qs = qs.filter(provider=provider)
    return [
        _row(
            occurred_at=row.purchased_at,
            kind='provider_purchase',
            layer='4_cash_to_providers',
            description=f'{row.provider} wallet top-up ({row.credits_or_units} units)',
            amount_ghs=row.amount_ghs,
            credits=row.credits_or_units,
            reference=row.provider_reference,
            provider=row.provider,
            channel=row.channel,
            administrator=_actor_label(row.recorded_by),
            detail={
                'effective_cost_per_unit_ghs': str(row.effective_cost_per_unit),
                'payment_method': row.payment_method,
            },
        )
        for row in qs.select_related('recorded_by')
    ]


def _provider_expenses(*, start, end, provider='', school_id=None):
    if school_id:
        return []
    qs = ProviderExpense.objects.filter(period_start__lte=end, period_end__gte=start)
    if provider:
        qs = qs.filter(provider=provider)
    return [
        _row(
            occurred_at=row.period_start,
            kind='provider_expense',
            layer='4_cash_to_providers',
            description=f'{row.provider} {row.expense_kind} expense',
            amount_ghs=row.amount_ghs,
            credits=row.units,
            reference=row.provider_reference,
            provider=row.provider,
            channel=row.channel,
            administrator=_actor_label(row.recorded_by),
            detail={
                'expense_kind': row.expense_kind,
                'period_start': row.period_start.isoformat(),
                'period_end': row.period_end.isoformat(),
                'source': row.source,
            },
        )
        for row in qs.select_related('recorded_by')
    ]


def _school_payments(*, start, end, school_id=None):
    qs = Payment.objects.filter(
        purpose=Payment.Purpose.TOPUP,
        status=Payment.Status.SUCCESS,
        created_at__gte=start,
        created_at__lte=end,
    ).select_related('school', 'topup_purchase')
    if school_id:
        qs = qs.filter(school_id=school_id)
    return [
        _row(
            occurred_at=row.paid_at or row.created_at,
            kind='school_topup_payment',
            layer='3_cash_from_schools',
            description='Communication credit top-up purchase',
            amount_ghs=row.amount_ghs,
            credits=getattr(row.topup_purchase, 'credits', None),
            reference=row.reference,
            school_id=row.school_id,
            school_name=row.school.name if row.school_id else '',
            provider=row.provider,
            channel=getattr(row.topup_purchase, 'channel', ''),
        )
        for row in qs
    ]


def _ledger_entries(*, start, end, school_id=None, channel=''):
    qs = CreditLedgerEntry.objects.filter(
        occurred_at__gte=start,
        occurred_at__lte=end,
    ).select_related('school', 'actor_platform_user')
    if school_id:
        qs = qs.filter(school_id=school_id)
    if channel:
        qs = qs.filter(channel=channel)
    return [
        _row(
            occurred_at=row.occurred_at,
            kind=LEDGER_TYPE_MAP.get(row.entry_type, row.entry_type),
            layer='2_school_credits',
            description=f'{row.get_entry_type_display()} ({row.channel})',
            credits=row.delta,
            reference=row.idempotency_key,
            school_id=row.school_id,
            school_name=row.school.name if row.school_id else '',
            channel=row.channel,
            administrator=_actor_label(row.actor_platform_user),
            detail={'balance_after': row.balance_after, 'metadata': row.metadata},
        )
        for row in qs
    ]


def _free_sponsored_sends(*, start, end, school_id=None, channel=''):
    from communications.services.aggregates import provider_accepted_statuses
    from notifications.models import GuardianDelivery

    qs = (
        GuardianDelivery.objects.filter(
            created_at__gte=start,
            created_at__lte=end,
            status__in=provider_accepted_statuses(),
        )
        .exclude(billing_classification=GuardianDelivery.BillingClassification.PAID)
        .select_related('school', 'allowance')
    )
    if school_id:
        qs = qs.filter(school_id=school_id)
    if channel:
        qs = qs.filter(channel=channel)
    return [
        _row(
            occurred_at=row.created_at,
            kind=f'{row.billing_classification}_send',
            layer='5_usage_economics',
            description=(
                f'{row.billing_classification.title()} {row.channel} send '
                f'({row.event_type})'
            ),
            amount_ghs=row.provider_cost_snapshot_ghs,
            credits=(row.segments if row.channel == 'sms' else 1),
            reference=row.idempotency_key,
            school_id=row.school_id,
            school_name=row.school.name if row.school_id else '',
            channel=row.channel,
            detail={
                'allowance': row.allowance.name if row.allowance_id else None,
                'status': row.status,
                'provider_cost_is_estimated': row.channel == 'email',
            },
        )
        for row in qs[:2000]
    ]


def _pricing_changes(*, start, end, school_id=None):
    if school_id:
        return []
    rows = []
    for config in SmsEncodingConfig.objects.filter(
        created_at__gte=start,
        created_at__lte=end,
    ).select_related('changed_by'):
        rows.append(
            _row(
                occurred_at=config.effective_from,
                kind='sms_pricing_change',
                layer='pricing_config',
                description=f'SMS pricing version ({config.encoding})',
                reference=str(config.pk),
                provider='arkesel',
                channel='sms',
                administrator=_actor_label(config.changed_by),
                detail={
                    'provider_cost_per_segment_ghs': str(
                        config.provider_cost_per_segment_ghs,
                    ),
                    'school_price_per_segment_ghs': str(
                        config.school_price_per_segment_ghs,
                    ),
                    'single_segment_limit': config.single_segment_limit,
                    'multipart_segment_limit': config.multipart_segment_limit,
                    'is_active': config.is_active,
                },
            ),
        )
    for config in EmailPricingConfig.objects.filter(
        created_at__gte=start,
        created_at__lte=end,
    ).select_related('changed_by'):
        rows.append(
            _row(
                occurred_at=config.effective_from,
                kind='email_pricing_change',
                layer='pricing_config',
                description='Email pricing version',
                reference=str(config.pk),
                provider='resend',
                channel='email',
                administrator=_actor_label(config.changed_by),
                detail={
                    'school_price_per_credit_ghs': str(
                        config.school_price_per_credit_ghs,
                    ),
                    'estimated_provider_cost_per_email_ghs': str(
                        config.estimated_provider_cost_per_email_ghs,
                    ),
                    'is_active': config.is_active,
                },
            ),
        )
    return rows


def _reconciliation_resolutions(*, start, end, school_id=None):
    qs = ProviderReconciliationItem.objects.filter(
        resolved_at__gte=start,
        resolved_at__lte=end,
    ).select_related('school', 'resolved_by', 'ledger_entry')
    if school_id:
        qs = qs.filter(school_id=school_id)
    return [
        _row(
            occurred_at=row.resolved_at,
            kind='reconciliation_resolution',
            layer='reconciliation',
            description=f'{row.discrepancy_type} → {row.resolution}',
            credits=row.ledger_entry.delta if row.ledger_entry_id else None,
            reference=str(row.pk),
            school_id=row.school_id,
            school_name=row.school.name if row.school_id else '',
            provider=row.provider,
            channel=row.channel,
            administrator=_actor_label(row.resolved_by),
            detail={
                'resolution_note': row.resolution_note,
                'ledger_entry_id': str(row.ledger_entry_id) if row.ledger_entry_id else None,
                'provider_message_id': row.provider_message_id,
            },
        )
        for row in qs
    ]


def transaction_feed(
    *,
    date_range,
    types: list[str] | None = None,
    school_id=None,
    provider: str = '',
    channel: str = '',
) -> list[dict]:
    """Unified, filterable feed sorted newest first."""
    start, end = date_range.start, date_range.end
    wanted = set(types or [])

    def want(*names) -> bool:
        return not wanted or bool(wanted.intersection(names))

    rows: list[dict] = []
    if want('provider_purchase'):
        rows += _provider_purchases(
            start=start,
            end=end,
            provider=provider,
            school_id=school_id,
        )
    if want('provider_expense'):
        rows += _provider_expenses(
            start=start,
            end=end,
            provider=provider,
            school_id=school_id,
        )
    if want('school_topup_payment'):
        rows += _school_payments(start=start, end=end, school_id=school_id)
    if want(
        'credit_allocation',
        'credit_topup',
        'credit_promo_grant',
        'credit_usage_debit',
        'credit_reversal',
        'credit_manual_adjust',
    ):
        ledger_rows = _ledger_entries(
            start=start,
            end=end,
            school_id=school_id,
            channel=channel,
        )
        if wanted:
            ledger_rows = [row for row in ledger_rows if row['type'] in wanted]
        rows += ledger_rows
    if want('free_send', 'sponsored_send'):
        send_rows = _free_sponsored_sends(
            start=start,
            end=end,
            school_id=school_id,
            channel=channel,
        )
        if wanted:
            send_rows = [row for row in send_rows if row['type'] in wanted]
        rows += send_rows
    if want('sms_pricing_change', 'email_pricing_change', 'pricing_change'):
        pricing_rows = _pricing_changes(start=start, end=end, school_id=school_id)
        if wanted and not wanted.intersection({'pricing_change'}):
            pricing_rows = [row for row in pricing_rows if row['type'] in wanted]
        rows += pricing_rows
    if want('reconciliation_resolution'):
        rows += _reconciliation_resolutions(start=start, end=end, school_id=school_id)

    if provider:
        rows = [row for row in rows if not row['provider'] or row['provider'] == provider]
    if channel:
        rows = [row for row in rows if not row['channel'] or row['channel'] == channel]

    rows.sort(key=lambda row: row['occurred_at'] or start, reverse=True)
    return rows
