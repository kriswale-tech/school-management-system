from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from billing.models import InvoiceLine, Plan, SchoolSubscription
from billing.services.capacity import (
    active_staff_count,
    active_student_count,
    current_subscription,
)
from billing.services.catalog import next_plan_covering_usage
from billing.services.discounts import apply_subscription_discount
from billing.services.invoices import create_invoice_with_lines, mark_invoice_paid
from billing.services.period import period_day_counts
from platform_admin.models import PlatformUser
from platform_admin.services.audit import record_audit


def _platform_actor(actor) -> PlatformUser | None:
    return actor if isinstance(actor, PlatformUser) else None


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.01'))


def compute_capacity_upgrade_proration(
    *,
    old_plan: Plan,
    new_plan: Plan,
    interval: str,
    period_start,
    period_end,
    now=None,
) -> dict:
    now = now or timezone.now()
    old_price = old_plan.price_for_interval(interval)
    new_price = new_plan.price_for_interval(interval)
    total_days, remaining_days = period_day_counts(
        period_start=period_start,
        period_end=period_end,
        now=now,
    )
    remaining_fraction = Decimal(remaining_days) / Decimal(total_days)
    amount_due = _quantize(max(Decimal('0.00'), (new_price - old_price) * remaining_fraction))
    return {
        'old_price_ghs': old_price,
        'new_price_ghs': new_price,
        'total_days': total_days,
        'remaining_days': remaining_days,
        'remaining_fraction': remaining_fraction,
        'amount_due_ghs': amount_due,
    }


@transaction.atomic
def apply_capacity_upgrade(
    *,
    school,
    new_plan: Plan | None = None,
    actor=None,
    ip_address: str | None = None,
    mark_paid: bool = True,
) -> tuple[SchoolSubscription, object]:
    """Immediate higher-plan upgrade with prorated application difference.

    Preserves ``current_period_end``. Communication add-ons are untouched (Phase 3).
    """
    subscription = current_subscription(school)
    if subscription is None:
        raise ValidationError({'detail': 'School has no current subscription.'})
    if not subscription.is_current:
        raise ValidationError({'detail': 'Only the current subscription can be upgraded.'})

    old_plan = subscription.plan
    students = active_student_count(school)
    staff = active_staff_count(school)
    target = new_plan or next_plan_covering_usage(
        current=old_plan,
        students=students,
        staff=staff,
    )
    if target is None:
        raise ValidationError({'plan': 'No higher capacity plan is available.'})
    if target.sort_order <= old_plan.sort_order:
        raise ValidationError({'plan': 'Target plan must be a higher capacity tier.'})

    # Capacity upgrades are allowed even when over the old max; new plan must cover
    # both student and staff usage (otherwise school remains blocked after "upgrade").
    if not target.covers_usage(students=students, staff=staff):
        raise ValidationError({
            'plan': (
                f'{target.name} cannot cover {students} students / {staff} staff. '
                'Choose a higher plan.'
            ),
        })

    now = timezone.now()
    proration = compute_capacity_upgrade_proration(
        old_plan=old_plan,
        new_plan=target,
        interval=subscription.interval,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end,
        now=now,
    )
    amount = proration['amount_due_ghs']
    lines = [
        {
            'kind': InvoiceLine.Kind.APPLICATION_PRORATION,
            'description': (
                f'Capacity upgrade {old_plan.name} → {target.name} '
                f'({proration["remaining_days"]}/{proration["total_days"]} days remaining)'
            ),
            'quantity': '1',
            'unit_price_ghs': str(amount),
            'amount_ghs': str(amount),
            'metadata': {
                'reason': 'capacity_upgrade',
                'old_plan_code': old_plan.code,
                'new_plan_code': target.code,
                'interval': subscription.interval,
                'old_price_ghs': str(proration['old_price_ghs']),
                'new_price_ghs': str(proration['new_price_ghs']),
                'remaining_days': proration['remaining_days'],
                'total_days': proration['total_days'],
            },
        },
    ]
    lines, _redemption = apply_subscription_discount(
        lines,
        subscription=subscription,
        period_start=now,
        period_end=subscription.current_period_end,
        period_origin=subscription.current_period_start,
        interval=subscription.interval,
    )
    invoice = create_invoice_with_lines(
        school=school,
        subscription=subscription,
        period_start=now,
        period_end=subscription.current_period_end,
        lines=lines,
        notes='Capacity-driven plan upgrade (prorated application difference)',
        mark_paid_if_zero=True,
    )
    # Phase 2: no Paystack yet — default mark_paid applies the plan immediately
    # and records a paid invoice (manual / complimentary until Phase 5).
    if mark_paid and invoice.status != invoice.Status.PAID:
        mark_invoice_paid(invoice)

    if invoice.status == invoice.Status.PAID:
        subscription.plan = target
        subscription.plan_code_snapshot = target.code
        subscription.capacity_max_snapshot = target.student_max
        subscription.staff_capacity_max_snapshot = target.staff_max
        subscription.app_price_snapshot_ghs = target.price_for_interval(subscription.interval)
        # Clear an ordinary pending upgrade to the same or lower plan if obsolete.
        if subscription.pending_plan_id and subscription.pending_plan.sort_order <= target.sort_order:
            subscription.pending_plan = None
            subscription.pending_interval = ''
            subscription.pending_change_effective_at = None
        subscription.save(
            update_fields=[
                'plan',
                'plan_code_snapshot',
                'capacity_max_snapshot',
                'staff_capacity_max_snapshot',
                'app_price_snapshot_ghs',
                'pending_plan',
                'pending_interval',
                'pending_change_effective_at',
                'updated_at',
            ],
        )

    record_audit(
        actor=_platform_actor(actor),
        action='billing.subscription.capacity_upgrade',
        target_type='school',
        target_id=str(school.pk),
        detail={
            'old_plan': old_plan.code,
            'new_plan': target.code,
            'invoice_id': str(invoice.pk),
            'amount_ghs': f'{invoice.total_ghs:.2f}',
            'period_end_unchanged': subscription.current_period_end.isoformat(),
            'plan_applied': invoice.status == invoice.Status.PAID,
            'recorded_as_paid': bool(
                mark_paid and invoice.status == invoice.Status.PAID
            ),
        },
        ip_address=ip_address,
    )
    return subscription, invoice


def quote_capacity_upgrade(*, school, new_plan: Plan) -> dict:
    """Prorated upgrade total, including the school's discount, without writing an invoice."""
    subscription = current_subscription(school)
    if subscription is None:
        raise ValidationError({'detail': 'School has no current subscription.'})

    old_plan = subscription.plan
    students = active_student_count(school)
    staff = active_staff_count(school)
    if new_plan.sort_order <= old_plan.sort_order:
        raise ValidationError({'plan': 'Target plan must be a higher capacity tier.'})
    if not new_plan.covers_usage(students=students, staff=staff):
        raise ValidationError({
            'plan': (
                f'{new_plan.name} cannot cover {students} students / {staff} staff. '
                'Choose a higher plan.'
            ),
        })

    now = timezone.now()
    proration = compute_capacity_upgrade_proration(
        old_plan=old_plan,
        new_plan=new_plan,
        interval=subscription.interval,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end,
        now=now,
    )
    lines = [
        {
            'kind': InvoiceLine.Kind.APPLICATION_PRORATION,
            'description': f'Capacity upgrade {old_plan.name} → {new_plan.name}',
            'quantity': '1',
            'unit_price_ghs': str(proration['amount_due_ghs']),
            'amount_ghs': str(proration['amount_due_ghs']),
            'metadata': {},
        },
    ]
    lines, _redemption = apply_subscription_discount(
        lines,
        subscription=subscription,
        period_start=now,
        period_end=subscription.current_period_end,
        period_origin=subscription.current_period_start,
        interval=subscription.interval,
        persist=False,
    )
    subtotal = Decimal('0.00')
    discount = Decimal('0.00')
    for line in lines:
        amount = Decimal(str(line['amount_ghs'])).quantize(Decimal('0.01'))
        if line['kind'] == InvoiceLine.Kind.DISCOUNT:
            discount += abs(amount)
        else:
            subtotal += amount
    total = max(Decimal('0.00'), subtotal - discount).quantize(Decimal('0.01'))
    return {
        'plan_code': new_plan.code,
        'plan_name': new_plan.name,
        'amount_ghs': f'{total:.2f}',
        'discount_ghs': f'{discount:.2f}',
        'remaining_days': proration['remaining_days'],
        'total_days': proration['total_days'],
    }


@transaction.atomic
def confirm_capacity_upgrade_payment(
    *,
    invoice,
    actor=None,
    ip_address: str | None = None,
) -> tuple[SchoolSubscription, object]:
    """Mark a capacity-upgrade invoice paid and apply the plan change."""
    if invoice.status == invoice.Status.PAID:
        subscription = invoice.subscription
        return subscription, invoice

    line = invoice.lines.filter(kind=InvoiceLine.Kind.APPLICATION_PRORATION).first()
    if line is None:
        raise ValidationError({'detail': 'Invoice is not a capacity upgrade proration.'})

    new_code = (line.metadata or {}).get('new_plan_code')
    if not new_code:
        raise ValidationError({'detail': 'Upgrade invoice is missing plan metadata.'})
    new_plan = Plan.objects.filter(code=new_code, is_active=True).first()
    if new_plan is None:
        raise ValidationError({'plan': 'Target plan no longer available.'})

    mark_invoice_paid(invoice)
    subscription = invoice.subscription
    subscription.plan = new_plan
    subscription.plan_code_snapshot = new_plan.code
    subscription.capacity_max_snapshot = new_plan.student_max
    subscription.staff_capacity_max_snapshot = new_plan.staff_max
    subscription.app_price_snapshot_ghs = new_plan.price_for_interval(subscription.interval)
    subscription.save(
        update_fields=[
            'plan',
            'plan_code_snapshot',
            'capacity_max_snapshot',
            'staff_capacity_max_snapshot',
            'app_price_snapshot_ghs',
            'updated_at',
        ],
    )
    record_audit(
        actor=_platform_actor(actor),
        action='billing.invoice.capacity_upgrade_paid',
        target_type='school',
        target_id=str(invoice.school_id),
        detail={'invoice_id': str(invoice.pk), 'new_plan': new_plan.code},
        ip_address=ip_address,
    )
    return subscription, invoice
