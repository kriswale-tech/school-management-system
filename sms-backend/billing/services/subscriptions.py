from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from billing.models import (
    InvoiceLine,
    Plan,
    SchoolSubscription,
    SubscriptionPeriod,
)
from billing.services.capacity import active_staff_count, active_student_count
from billing.services.catalog import FIRST_YEAR_FREE_CODE, plan_for_usage
from billing.services.discounts import apply_subscription_discount
from billing.services.invoices import create_invoice_with_lines
from billing.services.period import add_billing_interval
from platform_admin.services.audit import record_audit


def _snapshot_subscription(subscription: SchoolSubscription) -> None:
    plan = subscription.plan
    subscription.plan_code_snapshot = plan.code
    subscription.capacity_max_snapshot = plan.student_max
    subscription.staff_capacity_max_snapshot = plan.staff_max
    subscription.app_price_snapshot_ghs = plan.price_for_interval(subscription.interval)
    subscription.save(
        update_fields=[
            'plan_code_snapshot',
            'capacity_max_snapshot',
            'staff_capacity_max_snapshot',
            'app_price_snapshot_ghs',
            'updated_at',
        ],
    )


def build_application_invoice_lines(*, plan: Plan, interval: str) -> list[dict]:
    price = plan.price_for_interval(interval)
    return [
        {
            'kind': InvoiceLine.Kind.APPLICATION,
            'description': f'{plan.name} application ({interval})',
            'quantity': '1',
            'unit_price_ghs': str(price),
            'amount_ghs': str(price),
            'metadata': {'plan_code': plan.code, 'interval': interval},
        },
    ]


@transaction.atomic
def start_subscription(
    *,
    school,
    plan: Plan | None = None,
    interval: str = SchoolSubscription.Interval.ANNUAL,
    apply_first_year_free: bool = False,
    sms_sku=None,
    email_sku=None,
    actor=None,
    ip_address: str | None = None,
) -> SchoolSubscription:
    if SchoolSubscription.objects.filter(school=school, is_current=True).exists():
        raise ValidationError({'detail': 'School already has a current subscription.'})

    plan = plan or plan_for_usage(
        students=active_student_count(school),
        staff=active_staff_count(school),
    )
    if interval not in SchoolSubscription.Interval.values:
        raise ValidationError({'interval': 'Invalid billing interval.'})

    from communications.services.addons import (
        build_addon_invoice_lines,
        validate_sku_for_subscription,
    )

    if sms_sku is not None:
        validate_sku_for_subscription(
            sku=sms_sku,
            channel='sms',
            interval=interval,
            plan=plan,
        )
    if email_sku is not None:
        validate_sku_for_subscription(
            sku=email_sku,
            channel='email',
            interval=interval,
            plan=plan,
        )

    now = timezone.now()
    period_end = add_billing_interval(now, interval)
    subscription = SchoolSubscription.objects.create(
        school=school,
        plan=plan,
        interval=interval,
        status=SchoolSubscription.Status.ACTIVE,
        is_current=True,
        current_period_start=now,
        current_period_end=period_end,
        sms_addon_enabled=sms_sku is not None,
        email_addon_enabled=email_sku is not None,
        sms_sku=sms_sku,
        email_sku=email_sku,
    )
    _snapshot_subscription(subscription)

    lines = build_application_invoice_lines(plan=plan, interval=interval)
    lines.extend(build_addon_invoice_lines(subscription))
    lines, redemption = apply_subscription_discount(
        lines,
        subscription=subscription,
        period_start=now,
        period_end=period_end,
        interval=interval,
        apply_first_year_free=apply_first_year_free,
    )
    invoice = create_invoice_with_lines(
        school=school,
        subscription=subscription,
        period_start=now,
        period_end=period_end,
        lines=lines,
        notes='Initial subscription period',
    )
    SubscriptionPeriod.objects.create(
        subscription=subscription,
        starts_at=now,
        ends_at=period_end,
        plan=plan,
        interval=interval,
        invoice=invoice,
    )

    record_audit(
        actor=actor,
        action='billing.subscription.started',
        target_type='school',
        target_id=str(school.pk),
        detail={
            'subscription_id': str(subscription.pk),
            'plan_code': plan.code,
            'interval': interval,
            'invoice_id': str(invoice.pk),
            'total_ghs': str(invoice.total_ghs),
            'first_year_free': bool(
                redemption and redemption.campaign.code == FIRST_YEAR_FREE_CODE
            ),
            'sms_sku': sms_sku.code if sms_sku is not None else None,
            'email_sku': email_sku.code if email_sku is not None else None,
        },
        ip_address=ip_address,
    )
    return subscription


@transaction.atomic
def schedule_plan_change(
    *,
    subscription: SchoolSubscription,
    plan: Plan | None = None,
    interval: str | None = None,
    actor=None,
    ip_address: str | None = None,
) -> SchoolSubscription:
    """Ordinary upgrade/downgrade / interval change — effective next period only."""
    if not subscription.is_current:
        raise ValidationError({'detail': 'Only the current subscription can be changed.'})
    if plan is None and interval is None:
        raise ValidationError({'detail': 'Provide a plan_code and/or interval to schedule.'})

    if interval is not None and interval not in SchoolSubscription.Interval.values:
        raise ValidationError({'interval': 'Invalid billing interval.'})

    students = active_student_count(subscription.school)
    staff = active_staff_count(subscription.school)

    if plan is not None:
        if not plan.covers_usage(students=students, staff=staff):
            raise ValidationError({
                'plan': (
                    f'Cannot schedule {plan.name}: school has {students} students / '
                    f'{staff} staff (plan max '
                    f'{plan.student_max if plan.student_max is not None else "∞"} students, '
                    f'{plan.staff_max if plan.staff_max is not None else "∞"} staff).'
                ),
            })
        # Scheduling the current plan clears a pending plan change.
        subscription.pending_plan = None if plan.pk == subscription.plan_id else plan

    if interval is not None:
        # Same as current clears a pending interval change.
        subscription.pending_interval = '' if interval == subscription.interval else interval

    has_pending = bool(
        subscription.pending_plan_id
        or subscription.pending_interval
        or subscription.pending_sms_enabled is not None
        or subscription.pending_email_enabled is not None
    )
    subscription.pending_change_effective_at = (
        subscription.current_period_end if has_pending else None
    )
    subscription.save(
        update_fields=[
            'pending_plan',
            'pending_interval',
            'pending_change_effective_at',
            'updated_at',
        ],
    )
    record_audit(
        actor=actor,
        action='billing.subscription.change_scheduled',
        target_type='school',
        target_id=str(subscription.school_id),
        detail={
            'pending_plan': subscription.pending_plan.code if subscription.pending_plan_id else None,
            'pending_interval': subscription.pending_interval or None,
            'effective_at': (
                subscription.pending_change_effective_at.isoformat()
                if subscription.pending_change_effective_at
                else None
            ),
        },
        ip_address=ip_address,
    )
    return subscription


@transaction.atomic
def apply_pending_changes(subscription: SchoolSubscription) -> SchoolSubscription:
    from communications.services.addons import apply_pending_addon_changes

    has_plan_change = bool(subscription.pending_plan_id or subscription.pending_interval)
    has_addon_change = (
        subscription.pending_sms_enabled is not None
        or subscription.pending_email_enabled is not None
    )
    if not has_plan_change and not has_addon_change:
        return subscription

    if subscription.pending_plan_id:
        subscription.plan = subscription.pending_plan
    if subscription.pending_interval:
        subscription.interval = subscription.pending_interval
    subscription.pending_plan = None
    subscription.pending_interval = ''
    # Keep pending_change_effective_at until addon apply clears if only addons —
    # cleared below after addon apply.
    subscription.save(
        update_fields=[
            'plan',
            'interval',
            'pending_plan',
            'pending_interval',
            'updated_at',
        ],
    )
    _snapshot_subscription(subscription)
    subscription = apply_pending_addon_changes(subscription)
    if (
        subscription.pending_plan_id is None
        and not subscription.pending_interval
        and subscription.pending_sms_enabled is None
        and subscription.pending_email_enabled is None
    ):
        subscription.pending_change_effective_at = None
        subscription.save(update_fields=['pending_change_effective_at', 'updated_at'])
    return subscription


@transaction.atomic
def open_renewal_period(
    *,
    subscription: SchoolSubscription,
    actor=None,
    ip_address: str | None = None,
) -> tuple[SchoolSubscription, object]:
    """Advance to the next period, applying pending plan/interval/addon changes."""
    from communications.services.addons import (
        allocate_period_addons,
        build_addon_invoice_lines,
    )

    subscription = (
        SchoolSubscription.objects.select_related(
            'plan',
            'pending_plan',
            'sms_sku',
            'email_sku',
            'pending_sms_sku',
            'pending_email_sku',
        )
        .get(pk=subscription.pk)
    )
    subscription = apply_pending_changes(subscription)
    subscription.refresh_from_db()
    start = subscription.current_period_end
    end = add_billing_interval(start, subscription.interval)
    lines = build_application_invoice_lines(
        plan=subscription.plan,
        interval=subscription.interval,
    )
    lines.extend(build_addon_invoice_lines(subscription))
    lines, _redemption = apply_subscription_discount(
        lines,
        subscription=subscription,
        period_start=start,
        period_end=end,
        interval=subscription.interval,
    )
    invoice = create_invoice_with_lines(
        school=subscription.school,
        subscription=subscription,
        period_start=start,
        period_end=end,
        lines=lines,
        notes='Renewal period',
        mark_paid_if_zero=True,
    )
    period = SubscriptionPeriod.objects.create(
        subscription=subscription,
        starts_at=start,
        ends_at=end,
        plan=subscription.plan,
        interval=subscription.interval,
        invoice=invoice,
    )
    subscription.current_period_start = start
    subscription.current_period_end = end
    if invoice.status == invoice.Status.PAID:
        subscription.status = SchoolSubscription.Status.ACTIVE
        subscription.grace_period_ends_at = None
        allocate_period_addons(
            subscription=subscription,
            period=period,
            invoice=invoice,
        )
    else:
        subscription.status = SchoolSubscription.Status.PAST_DUE
        from platform_admin.services.settings import get_platform_settings

        grace_days = get_platform_settings().subscription_grace_days
        subscription.grace_period_ends_at = timezone.now() + timedelta(days=grace_days)
    subscription.save(
        update_fields=[
            'current_period_start',
            'current_period_end',
            'status',
            'grace_period_ends_at',
            'updated_at',
        ],
    )
    _snapshot_subscription(subscription)
    record_audit(
        actor=actor,
        action='billing.subscription.renewed',
        target_type='school',
        target_id=str(subscription.school_id),
        detail={
            'period_id': str(period.pk),
            'invoice_id': str(invoice.pk),
            'total_ghs': str(invoice.total_ghs),
            'sms_addon': subscription.sms_addon_enabled,
            'email_addon': subscription.email_addon_enabled,
        },
        ip_address=ip_address,
    )
    return subscription, invoice
