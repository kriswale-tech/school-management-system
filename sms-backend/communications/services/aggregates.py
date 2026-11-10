"""Shared messaging aggregations, strictly separated by money layer (v4.1 §2.5).

Every helper here returns figures for exactly ONE of the five layers. Nothing in
this module ever adds a provider balance to a school balance, or cash received
to usage value. Callers must keep them in separate response keys.
"""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce

from billing.models import Invoice, InvoiceLine, Payment
from communications.models import (
    CreditAccount,
    CreditLedgerEntry,
    Provider,
    ProviderBalanceSnapshot,
    ProviderExpense,
    ProviderPurchase,
    ResendUsageSnapshot,
)

SMS = 'sms'
EMAIL = 'email'
CHANNELS = (SMS, EMAIL)

CLASSIFICATIONS = ('paid', 'free', 'sponsored')

_ZERO = Decimal('0')
_MONEY = DecimalField(max_digits=18, decimal_places=6)


def _money(value) -> Decimal:
    return Decimal(value) if value is not None else _ZERO


def provider_accepted_statuses() -> list[str]:
    """Statuses that imply the provider accepted the send, so cost was incurred.

    ``failed`` is included: a failed DLR arrives *after* acceptance, so the
    provider units were consumed even if a refund was later issued to the
    school. Revenue is taken from the ledger (charged − refunded) rather than
    from this filter, so a refunded failure costs us without crediting revenue.
    """
    from notifications.models import GuardianDelivery

    return [
        GuardianDelivery.Status.SUBMITTED,
        GuardianDelivery.Status.DELIVERED,
        GuardianDelivery.Status.FAILED,
        GuardianDelivery.Status.SENT,
    ]


def delivered_statuses() -> list[str]:
    """Accepted and not known to have failed."""
    from notifications.models import GuardianDelivery

    return [
        GuardianDelivery.Status.SUBMITTED,
        GuardianDelivery.Status.DELIVERED,
        GuardianDelivery.Status.SENT,
    ]


# ---------------------------------------------------------------------------
# Layer 5 — usage economics (delivery rows + pricing snapshots)
# ---------------------------------------------------------------------------

def guardian_deliveries(
    *,
    start=None,
    end=None,
    channel: str | None = None,
    classification: str | None = None,
    school=None,
    event_type: str | None = None,
    accepted_only: bool = True,
):
    from notifications.models import GuardianDelivery

    qs = GuardianDelivery.objects.all()
    if start is not None:
        qs = qs.filter(created_at__gte=start)
    if end is not None:
        qs = qs.filter(created_at__lte=end)
    if channel:
        qs = qs.filter(channel=channel)
    if classification:
        qs = qs.filter(billing_classification=classification)
    if school is not None:
        qs = qs.filter(school=school)
    if event_type:
        qs = qs.filter(event_type=event_type)
    if accepted_only:
        qs = qs.filter(status__in=provider_accepted_statuses())
    return qs


def units_expression(channel: str):
    """Billable units per row: SMS counts segments, email counts recipients."""
    if channel == SMS:
        return Coalesce(Sum('segments'), Value(0))
    return Count('id')


def delivery_usage_metrics(queryset, *, channel: str) -> dict:
    """Volumes and snapshot-valued economics for one channel's delivery rows.

    ``unpriced_rows`` is reported explicitly: pre-v4.1 deliveries have no cost
    snapshots and must never be re-valued with today's config.
    """
    aggregate = queryset.aggregate(
        messages=Count('id'),
        segments=Coalesce(Sum('segments'), Value(0)),
        provider_cost_ghs=Coalesce(Sum('provider_cost_snapshot_ghs'), Value(_ZERO, _MONEY)),
        sell_value_ghs=Coalesce(
            Sum('school_unit_price_snapshot_ghs'),
            Value(_ZERO, _MONEY),
        ),
        credits_charged=Coalesce(Sum('credits_charged'), Value(0)),
        credits_refunded=Coalesce(Sum('credits_refunded'), Value(0)),
        unpriced_rows=Count('id', filter=Q(provider_cost_snapshot_ghs__isnull=True)),
        unbilled_rows=Count('id', filter=Q(unbilled=True)),
    )
    messages = int(aggregate['messages'] or 0)
    segments = int(aggregate['segments'] or 0)
    units = segments if channel == SMS else messages
    return {
        'messages': messages,
        'segments': segments if channel == SMS else 0,
        'units': units,
        'credits_charged': int(aggregate['credits_charged'] or 0),
        'credits_refunded': int(aggregate['credits_refunded'] or 0),
        'provider_cost_ghs': _money(aggregate['provider_cost_ghs']),
        'usage_valued_revenue_ghs': _money(aggregate['sell_value_ghs']),
        'unpriced_rows': int(aggregate['unpriced_rows'] or 0),
        'unbilled_rows': int(aggregate['unbilled_rows'] or 0),
    }


def delivery_status_counts(queryset) -> dict:
    from notifications.models import GuardianDelivery

    aggregate = queryset.aggregate(
        submitted=Count('id', filter=Q(status=GuardianDelivery.Status.SUBMITTED)),
        delivered=Count('id', filter=Q(status=GuardianDelivery.Status.DELIVERED)),
        failed=Count('id', filter=Q(status=GuardianDelivery.Status.FAILED)),
        unknown=Count('id', filter=Q(status=GuardianDelivery.Status.UNKNOWN)),
        skipped=Count('id', filter=Q(status=GuardianDelivery.Status.SKIPPED)),
    )
    return {key: int(value or 0) for key, value in aggregate.items()}


def classification_breakdown(*, start, end, channel: str, school=None) -> dict:
    """Usage metrics split by paid / free / sponsored for one channel."""
    out = {}
    for classification in CLASSIFICATIONS:
        qs = guardian_deliveries(
            start=start,
            end=end,
            channel=channel,
            classification=classification,
            school=school,
        )
        out[classification] = delivery_usage_metrics(qs, channel=channel)
    return out


# ---------------------------------------------------------------------------
# Platform-funded traffic (OTP / staff email) — never a school debit
# ---------------------------------------------------------------------------

def platform_outbound_metrics(*, start, end, channel: str | None = None) -> dict:
    from notifications.models import PlatformOutboundDelivery

    qs = PlatformOutboundDelivery.objects.filter(created_at__gte=start, created_at__lte=end)
    if channel:
        qs = qs.filter(channel=channel)
    aggregate = qs.aggregate(
        messages=Count('id'),
        sms_messages=Count('id', filter=Q(channel=PlatformOutboundDelivery.Channel.SMS)),
        email_messages=Count('id', filter=Q(channel=PlatformOutboundDelivery.Channel.EMAIL)),
        segments=Coalesce(Sum('segments'), Value(0)),
        provider_cost_ghs=Coalesce(Sum('provider_cost_snapshot_ghs'), Value(_ZERO, _MONEY)),
        failed=Count('id', filter=Q(status=PlatformOutboundDelivery.Status.FAILED)),
    )
    by_purpose = {
        row['purpose']: int(row['count'] or 0)
        for row in qs.values('purpose').annotate(count=Count('id'))
    }
    return {
        'messages': int(aggregate['messages'] or 0),
        'sms_messages': int(aggregate['sms_messages'] or 0),
        'email_messages': int(aggregate['email_messages'] or 0),
        'sms_segments': int(aggregate['segments'] or 0),
        'failed': int(aggregate['failed'] or 0),
        'provider_cost_ghs': _money(aggregate['provider_cost_ghs']),
        'by_purpose': by_purpose,
        'school_ledger_debits': 0,  # structural: v4 invariant 4
    }


# ---------------------------------------------------------------------------
# Layer 2 — school credits (units)
# ---------------------------------------------------------------------------

def ledger_unit_metrics(*, start, end, channel: str, school=None) -> dict:
    qs = CreditLedgerEntry.objects.filter(
        channel=channel,
        occurred_at__gte=start,
        occurred_at__lte=end,
    )
    if school is not None:
        qs = qs.filter(school=school)
    aggregate = qs.aggregate(
        allocation_recurring=Coalesce(
            Sum('delta', filter=Q(entry_type=CreditLedgerEntry.EntryType.ALLOCATION_RECURRING)),
            Value(0),
        ),
        topup=Coalesce(
            Sum('delta', filter=Q(entry_type=CreditLedgerEntry.EntryType.TOPUP)),
            Value(0),
        ),
        promo_grant=Coalesce(
            Sum('delta', filter=Q(entry_type=CreditLedgerEntry.EntryType.PROMO_GRANT)),
            Value(0),
        ),
        manual_adjust_positive=Coalesce(
            Sum(
                'delta',
                filter=Q(
                    entry_type=CreditLedgerEntry.EntryType.MANUAL_ADJUST,
                    delta__gt=0,
                ),
            ),
            Value(0),
        ),
        manual_adjust_negative=Coalesce(
            Sum(
                'delta',
                filter=Q(
                    entry_type=CreditLedgerEntry.EntryType.MANUAL_ADJUST,
                    delta__lt=0,
                ),
            ),
            Value(0),
        ),
        usage_debit=Coalesce(
            Sum('delta', filter=Q(entry_type=CreditLedgerEntry.EntryType.USAGE_DEBIT)),
            Value(0),
        ),
        reversal=Coalesce(
            Sum('delta', filter=Q(entry_type=CreditLedgerEntry.EntryType.REVERSAL)),
            Value(0),
        ),
    )
    allocated = (
        int(aggregate['allocation_recurring'] or 0)
        + int(aggregate['topup'] or 0)
        + int(aggregate['promo_grant'] or 0)
        + int(aggregate['manual_adjust_positive'] or 0)
    )
    consumed = abs(int(aggregate['usage_debit'] or 0)) - int(aggregate['reversal'] or 0)
    return {
        'allocated_units': allocated,
        'allocation_recurring_units': int(aggregate['allocation_recurring'] or 0),
        'topup_units': int(aggregate['topup'] or 0),
        'promo_grant_units': int(aggregate['promo_grant'] or 0),
        'manual_adjust_units': (
            int(aggregate['manual_adjust_positive'] or 0)
            + int(aggregate['manual_adjust_negative'] or 0)
        ),
        'usage_debit_units': abs(int(aggregate['usage_debit'] or 0)),
        'reversal_units': int(aggregate['reversal'] or 0),
        'consumed_units': max(0, consumed),
    }


def school_balances(*, channel: str | None = None, school=None) -> dict:
    """Cached balances — a delivery liability, never consumed revenue."""
    qs = CreditAccount.objects.all()
    if channel:
        qs = qs.filter(channel=channel)
    if school is not None:
        qs = qs.filter(school=school)
    rows = qs.values('channel').annotate(total=Coalesce(Sum('balance'), Value(0)))
    out = {SMS: 0, EMAIL: 0}
    for row in rows:
        out[row['channel']] = int(row['total'] or 0)
    return out


# ---------------------------------------------------------------------------
# Layer 3 — cash from schools (GHS)
# ---------------------------------------------------------------------------

def comms_cash_from_schools(*, start, end, school=None) -> dict:
    """Successful school payments attributable to communications.

    Top-ups count in full. Invoice payments count only the SMS/email add-on
    lines on that invoice, capped at the amount actually paid, so application
    subscription revenue is never mis-booked as messaging revenue.
    """
    payments = Payment.objects.filter(
        status=Payment.Status.SUCCESS,
        created_at__gte=start,
        created_at__lte=end,
    )
    if school is not None:
        payments = payments.filter(school=school)

    topup_total = _money(
        payments.filter(purpose=Payment.Purpose.TOPUP).aggregate(
            total=Coalesce(Sum('amount_ghs'), Value(_ZERO, _MONEY)),
        )['total'],
    )

    invoice_payments = list(
        payments.filter(purpose=Payment.Purpose.INVOICE)
        .exclude(invoice__isnull=True)
        .values('invoice_id', 'amount_ghs'),
    )
    invoice_ids = [row['invoice_id'] for row in invoice_payments]
    comms_by_invoice: dict = {}
    sms_by_invoice: dict = {}
    email_by_invoice: dict = {}
    if invoice_ids:
        for row in (
            InvoiceLine.objects.filter(
                invoice_id__in=invoice_ids,
                kind__in=[InvoiceLine.Kind.SMS_ADDON, InvoiceLine.Kind.EMAIL_ADDON],
            )
            .values('invoice_id', 'kind')
            .annotate(total=Coalesce(Sum('amount_ghs'), Value(_ZERO, _MONEY)))
        ):
            amount = _money(row['total'])
            comms_by_invoice[row['invoice_id']] = (
                comms_by_invoice.get(row['invoice_id'], _ZERO) + amount
            )
            if row['kind'] == InvoiceLine.Kind.SMS_ADDON:
                sms_by_invoice[row['invoice_id']] = amount
            else:
                email_by_invoice[row['invoice_id']] = amount

    addon_total = _ZERO
    addon_sms = _ZERO
    addon_email = _ZERO
    for row in invoice_payments:
        invoice_id = row['invoice_id']
        comms_amount = comms_by_invoice.get(invoice_id, _ZERO)
        if comms_amount <= 0:
            continue
        paid = _money(row['amount_ghs'])
        attributable = min(comms_amount, paid)
        addon_total += attributable
        if comms_amount > 0:
            share = attributable / comms_amount
            addon_sms += sms_by_invoice.get(invoice_id, _ZERO) * share
            addon_email += email_by_invoice.get(invoice_id, _ZERO) * share

    topups_by_channel = {SMS: _ZERO, EMAIL: _ZERO}
    for row in (
        payments.filter(purpose=Payment.Purpose.TOPUP)
        .exclude(topup_purchase__isnull=True)
        .values('topup_purchase__channel')
        .annotate(total=Coalesce(Sum('amount_ghs'), Value(_ZERO, _MONEY)))
    ):
        channel_key = row['topup_purchase__channel']
        if channel_key in topups_by_channel:
            topups_by_channel[channel_key] = _money(row['total'])

    return {
        'topup_cash_ghs': topup_total,
        'addon_cash_ghs': addon_total,
        'total_cash_ghs': topup_total + addon_total,
        'sms_cash_ghs': topups_by_channel[SMS] + addon_sms,
        'email_cash_ghs': topups_by_channel[EMAIL] + addon_email,
    }


def unpaid_comms_invoice_total(*, start, end) -> Decimal:
    """Billed-but-unsettled communications add-on value (context, not revenue)."""
    return _money(
        InvoiceLine.objects.filter(
            kind__in=[InvoiceLine.Kind.SMS_ADDON, InvoiceLine.Kind.EMAIL_ADDON],
            invoice__created_at__gte=start,
            invoice__created_at__lte=end,
        )
        .exclude(invoice__status=Invoice.Status.PAID)
        .aggregate(total=Coalesce(Sum('amount_ghs'), Value(_ZERO, _MONEY)))['total'],
    )


# ---------------------------------------------------------------------------
# Layers 1 & 4 — provider wallet / plan and cash to providers (GHS)
# ---------------------------------------------------------------------------

def provider_purchase_metrics(*, start, end, provider: str | None = None) -> dict:
    qs = ProviderPurchase.objects.filter(purchased_at__gte=start, purchased_at__lte=end)
    if provider:
        qs = qs.filter(provider=provider)
    aggregate = qs.aggregate(
        count=Count('id'),
        amount_ghs=Coalesce(Sum('amount_ghs'), Value(_ZERO, _MONEY)),
        units=Coalesce(Sum('credits_or_units'), Value(0)),
    )
    units = int(aggregate['units'] or 0)
    amount = _money(aggregate['amount_ghs'])
    return {
        'purchase_count': int(aggregate['count'] or 0),
        'amount_ghs': amount,
        'units_purchased': units,
        'blended_cost_per_unit_ghs': (
            (amount / Decimal(units)).quantize(Decimal('0.000001')) if units else None
        ),
    }


def provider_expense_metrics(*, start, end, provider: str | None = None) -> dict:
    qs = ProviderExpense.objects.filter(period_start__lte=end, period_end__gte=start)
    if provider:
        qs = qs.filter(provider=provider)
    aggregate = qs.aggregate(
        count=Count('id'),
        total_amount=Coalesce(Sum('amount_ghs'), Value(_ZERO, _MONEY)),
        subscription_total=Coalesce(
            Sum('amount_ghs', filter=Q(expense_kind=ProviderExpense.ExpenseKind.SUBSCRIPTION)),
            Value(_ZERO, _MONEY),
        ),
        overage_total=Coalesce(
            Sum('amount_ghs', filter=Q(expense_kind=ProviderExpense.ExpenseKind.OVERAGE)),
            Value(_ZERO, _MONEY),
        ),
        other_total=Coalesce(
            Sum('amount_ghs', filter=Q(expense_kind=ProviderExpense.ExpenseKind.OTHER)),
            Value(_ZERO, _MONEY),
        ),
    )
    return {
        'expense_count': int(aggregate['count'] or 0),
        'amount_ghs': _money(aggregate['total_amount']),
        'subscription_ghs': _money(aggregate['subscription_total']),
        'overage_ghs': _money(aggregate['overage_total']),
        'other_ghs': _money(aggregate['other_total']),
    }


def latest_provider_balance() -> dict:
    snapshot = (
        ProviderBalanceSnapshot.objects.filter(
            provider_account__provider=Provider.ARKESEL,
        )
        .select_related('provider_account')
        .order_by('-captured_at')
        .first()
    )
    if snapshot is None:
        return {
            'provider': Provider.ARKESEL,
            'sms_balance': None,
            'main_balance_text': '',
            'captured_at': None,
            'source': None,
        }
    return {
        'provider': Provider.ARKESEL,
        'sms_balance': snapshot.sms_balance,
        'main_balance_text': snapshot.main_balance_text,
        'captured_at': snapshot.captured_at,
        'source': snapshot.source,
    }


def latest_resend_usage() -> dict:
    """Email provider usage snapshot — prefers Amazon SES, falls back to legacy Resend."""
    snapshot = (
        ResendUsageSnapshot.objects.filter(provider_account__provider=Provider.SES)
        .select_related('provider_account')
        .order_by('-captured_at')
        .first()
    )
    if snapshot is None:
        snapshot = (
            ResendUsageSnapshot.objects.filter(provider_account__provider=Provider.RESEND)
            .select_related('provider_account')
            .order_by('-captured_at')
            .first()
        )
    if snapshot is None:
        return {
            'monthly_used': None,
            'monthly_limit': None,
            'daily_used': None,
            'daily_limit': None,
            'captured_at': None,
            'source': None,
            'provider': None,
        }
    return {
        'monthly_used': snapshot.monthly_used,
        'monthly_limit': snapshot.monthly_limit,
        'daily_used': snapshot.daily_used,
        'daily_limit': snapshot.daily_limit,
        'captured_at': snapshot.captured_at,
        'source': snapshot.source,
        'provider': snapshot.provider_account.provider,
    }
