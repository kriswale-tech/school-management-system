from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from billing.models import InvoiceLine, SchoolSubscription
from billing.services.invoices import create_invoice_with_lines, mark_invoice_paid
from billing.services.period import add_billing_interval, period_day_counts
from platform_admin.models import PlatformUser
from platform_admin.services.audit import record_audit


def _platform_actor(actor) -> PlatformUser | None:
    return actor if isinstance(actor, PlatformUser) else None


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.01'))


def compute_interval_change_proration(
    *,
    plan,
    old_interval: str,
    new_interval: str,
    period_start,
    period_end,
    now=None,
) -> dict:
    now = now or timezone.now()
    old_price = plan.price_for_interval(old_interval)
    new_price = plan.price_for_interval(new_interval)
    total_days, remaining_days = period_day_counts(
        period_start=period_start,
        period_end=period_end,
        now=now,
    )
    remaining_fraction = Decimal(remaining_days) / Decimal(total_days)
    unused_credit = _quantize(old_price * remaining_fraction)
    new_period_end = add_billing_interval(now, new_interval)
    amount_due = _quantize(max(Decimal('0.00'), new_price - unused_credit))
    return {
        'old_price_ghs': old_price,
        'new_price_ghs': new_price,
        'unused_credit_ghs': unused_credit,
        'amount_due_ghs': amount_due,
        'total_days': total_days,
        'remaining_days': remaining_days,
        'new_period_start': now,
        'new_period_end': new_period_end,
    }


@transaction.atomic
def apply_interval_change_to_subscription(
    *,
    subscription: SchoolSubscription,
    new_interval: str,
    invoice,
) -> SchoolSubscription:
    """Apply interval + period after the interval-change invoice is paid (or zero)."""
    line = invoice.lines.filter(kind=InvoiceLine.Kind.INTERVAL_CHANGE).first()
    if line is None:
        raise ValidationError({'detail': 'Invoice is not an interval change.'})
    meta = line.metadata or {}
    target = meta.get('new_interval') or new_interval
    if target not in SchoolSubscription.Interval.values:
        raise ValidationError({'interval': 'Invalid billing interval on invoice.'})

    new_start = invoice.period_start
    new_end = invoice.period_end
    subscription.interval = target
    subscription.current_period_start = new_start
    subscription.current_period_end = new_end
    # Clear a pending interval that is now obsolete.
    if subscription.pending_interval:
        subscription.pending_interval = ''
        if subscription.pending_plan_id is None:
            subscription.pending_change_effective_at = None
    subscription.app_price_snapshot_ghs = subscription.plan.price_for_interval(target)
    subscription.save(
        update_fields=[
            'interval',
            'current_period_start',
            'current_period_end',
            'pending_interval',
            'pending_change_effective_at',
            'app_price_snapshot_ghs',
            'updated_at',
        ],
    )
    return subscription


@transaction.atomic
def confirm_interval_change_payment(
    *,
    invoice,
    actor=None,
    ip_address: str | None = None,
) -> tuple[SchoolSubscription, object]:
    if invoice.status != invoice.Status.PAID:
        mark_invoice_paid(invoice)
    subscription = invoice.subscription
    if invoice.lines.filter(kind=InvoiceLine.Kind.INTERVAL_CHANGE).exists():
        # Only apply once — detect if period already matches invoice.
        line = invoice.lines.filter(kind=InvoiceLine.Kind.INTERVAL_CHANGE).first()
        meta = line.metadata or {}
        target = meta.get('new_interval')
        already = (
            subscription.interval == target
            and subscription.current_period_start == invoice.period_start
            and subscription.current_period_end == invoice.period_end
        )
        if not already:
            subscription = apply_interval_change_to_subscription(
                subscription=subscription,
                new_interval=target,
                invoice=invoice,
            )
    from billing.services.dunning import reactivate_subscription_after_payment

    subscription = reactivate_subscription_after_payment(
        subscription=subscription,
        actor=_platform_actor(actor),
        ip_address=ip_address,
    )
    record_audit(
        actor=_platform_actor(actor),
        action='billing.invoice.interval_change_paid',
        target_type='school',
        target_id=str(invoice.school_id),
        detail={
            'invoice_id': str(invoice.pk),
            'new_interval': subscription.interval,
        },
        ip_address=ip_address,
    )
    return subscription, invoice


def change_billing_interval(
    *,
    school,
    new_interval: str,
    actor=None,
    ip_address: str | None = None,
    mark_paid: bool = False,
) -> tuple[SchoolSubscription, object]:
    """Mid-period interval switches are disabled.

    Schedule with ``schedule_plan_change(..., interval=...)`` instead so the
    change applies at the next renewal.
    """
    raise ValidationError({
        'detail': (
            'Billing interval can only be changed at the next renewal. '
            'Schedule the new interval instead of switching mid-period.'
        ),
    })
