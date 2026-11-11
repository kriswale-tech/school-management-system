from __future__ import annotations

from decimal import Decimal

from billing.models import Invoice, InvoiceLine, Plan, SchoolSubscription
from billing.services.period import add_billing_interval
from billing.services.discounts import apply_subscription_discount
from billing.services.subscriptions import build_application_invoice_lines
from communications.models import CommunicationAddonSku
from communications.services.catalog import default_sku_for


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.01'))


def _effective_addon_state(subscription: SchoolSubscription, channel: str) -> tuple[bool, object | None]:
    if channel == 'sms':
        if subscription.pending_sms_enabled is not None:
            enabled = bool(subscription.pending_sms_enabled)
            sku = subscription.pending_sms_sku if enabled else None
        else:
            enabled = bool(subscription.sms_addon_enabled)
            sku = subscription.sms_sku if enabled else None
    else:
        if subscription.pending_email_enabled is not None:
            enabled = bool(subscription.pending_email_enabled)
            sku = subscription.pending_email_sku if enabled else None
        else:
            enabled = bool(subscription.email_addon_enabled)
            sku = subscription.email_sku if enabled else None
    return enabled, sku


def _sku_for_interval(sku, *, channel: str, interval: str):
    if sku is not None and sku.interval == interval and sku.is_active:
        return sku
    return default_sku_for(channel=channel, interval=interval)


def build_upcoming_renewal_preview(subscription: SchoolSubscription) -> dict:
    """Estimate the next renewal invoice using pending plan/interval/addon changes."""
    plan: Plan = subscription.pending_plan or subscription.plan
    interval = subscription.pending_interval or subscription.interval
    if interval not in SchoolSubscription.Interval.values:
        interval = subscription.interval

    period_start = subscription.current_period_end
    period_end = add_billing_interval(period_start, interval)

    lines = build_application_invoice_lines(plan=plan, interval=interval)

    sms_enabled, sms_sku = _effective_addon_state(subscription, 'sms')
    email_enabled, email_sku = _effective_addon_state(subscription, 'email')
    if sms_enabled:
        sms_sku = _sku_for_interval(
            sms_sku,
            channel=CommunicationAddonSku.Channel.SMS,
            interval=interval,
        )
        if sms_sku is not None:
            lines.append({
                'kind': InvoiceLine.Kind.SMS_ADDON,
                'description': f'{sms_sku.name} ({sms_sku.credits_per_period} SMS credits)',
                'quantity': '1',
                'unit_price_ghs': str(sms_sku.price_ghs),
                'amount_ghs': str(sms_sku.price_ghs),
                'metadata': {
                    'sku_code': sms_sku.code,
                    'credits': sms_sku.credits_per_period,
                    'channel': 'sms',
                },
            })
    if email_enabled:
        email_sku = _sku_for_interval(
            email_sku,
            channel=CommunicationAddonSku.Channel.EMAIL,
            interval=interval,
        )
        if email_sku is not None:
            lines.append({
                'kind': InvoiceLine.Kind.EMAIL_ADDON,
                'description': (
                    f'{email_sku.name} ({email_sku.credits_per_period} email credits)'
                ),
                'quantity': '1',
                'unit_price_ghs': str(email_sku.price_ghs),
                'amount_ghs': str(email_sku.price_ghs),
                'metadata': {
                    'sku_code': email_sku.code,
                    'credits': email_sku.credits_per_period,
                    'channel': 'email',
                },
            })

    lines, redemption = apply_subscription_discount(
        lines,
        subscription=subscription,
        period_start=period_start,
        period_end=period_end,
        interval=interval,
        persist=False,
    )

    subtotal = Decimal('0.00')
    discount = Decimal('0.00')
    for line in lines:
        amount = _quantize(Decimal(str(line['amount_ghs'])))
        if line['kind'] == InvoiceLine.Kind.DISCOUNT:
            discount += abs(amount)
        else:
            subtotal += amount
    total = _quantize(max(Decimal('0.00'), subtotal - discount))

    due_now = (
        Invoice.objects.filter(
            school_id=subscription.school_id,
            status=Invoice.Status.OPEN,
        )
        .exclude(lines__kind__in=[InvoiceLine.Kind.INTERVAL_CHANGE, InvoiceLine.Kind.TOPUP])
        .order_by('-created_at')
        .prefetch_related('lines')
        .first()
    )

    return {
        'kind': 'renewal',
        'due_at': period_start,
        'period_start': period_start,
        'period_end': period_end,
        'plan_code': plan.code,
        'plan_name': plan.name,
        'interval': interval,
        'currency': 'GHS',
        'subtotal_ghs': str(subtotal),
        'discount_ghs': str(discount),
        'total_ghs': str(total),
        'discount_label': (
            redemption.campaign.name if redemption is not None else None
        ),
        'lines': [
            {
                'kind': line['kind'],
                'description': line['description'],
                'amount_ghs': str(_quantize(Decimal(str(line['amount_ghs'])))),
                'metadata': line.get('metadata') or {},
            }
            for line in lines
        ],
        'includes_pending_changes': bool(
            subscription.pending_plan_id
            or subscription.pending_interval
            or subscription.pending_sms_enabled is not None
            or subscription.pending_email_enabled is not None
        ),
        'open_invoice_id': str(due_now.pk) if due_now else None,
        'open_invoice_total_ghs': str(due_now.total_ghs) if due_now else None,
        'open_invoice_notes': due_now.notes if due_now else '',
    }
