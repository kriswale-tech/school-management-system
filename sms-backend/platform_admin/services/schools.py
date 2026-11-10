from __future__ import annotations

from django.db import transaction
from django.db.models import (
    BooleanField,
    Count,
    Exists,
    ExpressionWrapper,
    F,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
)
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.models import SchoolMembership, User
from accounts.services.registration import _provision_school
from billing.models import Invoice, SchoolSubscription
from platform_admin.models import PlatformUser
from platform_admin.services.audit import record_audit
from schools.models import School
from students.models import Student

RENEWING_SUBSCRIPTION_STATUSES = {
    SchoolSubscription.Status.ACTIVE,
    SchoolSubscription.Status.PAST_DUE,
}


def _payment_overdue_annotation():
    """True when the current subscription is unpaid or an open invoice is past due."""
    overdue_subscription = SchoolSubscription.objects.filter(
        school_id=OuterRef('pk'),
        is_current=True,
    ).filter(
        Q(status=SchoolSubscription.Status.PAST_DUE) | Q(billing_suspended_school=True),
    )
    overdue_invoice = Invoice.objects.filter(
        school_id=OuterRef('pk'),
        status=Invoice.Status.OPEN,
        due_at__lt=timezone.now(),
        total_ghs__gt=F('amount_paid_ghs'),
    )
    return ExpressionWrapper(
        Exists(overdue_subscription) | Exists(overdue_invoice),
        output_field=BooleanField(),
    )


def school_queryset() -> QuerySet[School]:
    """Annotate directory counts without cross-join inflation.

    Both Counts must use ``distinct=True`` when combined, otherwise Django's
    JOIN multiplies memberships × students (e.g. 4×154 → 616).
    """
    current_subscriptions = SchoolSubscription.objects.filter(is_current=True).select_related(
        'plan',
    )
    admin_memberships = (
        SchoolMembership.objects.filter(
            is_active=True,
            role=User.RoleChoices.ADMIN,
        )
        .select_related('user')
        .order_by('created_at')
    )
    return (
        School.objects.annotate(
            staff_count=Count(
                'memberships',
                filter=Q(memberships__is_active=True),
                distinct=True,
            ),
            student_count=Count(
                'students',
                filter=Q(students__is_active=True),
                distinct=True,
            ),
            payment_overdue=_payment_overdue_annotation(),
        )
        .prefetch_related(
            Prefetch(
                'subscriptions',
                queryset=current_subscriptions,
                to_attr='current_subscriptions',
            ),
            Prefetch(
                'memberships',
                queryset=admin_memberships,
                to_attr='admin_memberships',
            ),
        )
        .order_by('name')
    )


def school_directory_summary() -> dict[str, int]:
    """Platform-wide directory totals, independent of list filters."""
    overdue = School.objects.annotate(payment_overdue=_payment_overdue_annotation()).filter(
        payment_overdue=True,
    )
    return {
        'school_count': School.objects.count(),
        'active_school_count': School.objects.filter(status=School.Status.ACTIVE).count(),
        'student_count': Student.objects.filter(is_active=True).count(),
        'staff_count': SchoolMembership.objects.filter(is_active=True).count(),
        'overdue_school_count': overdue.count(),
    }


def current_subscription(school: School) -> SchoolSubscription | None:
    cached = getattr(school, 'current_subscriptions', None)
    if cached is not None:
        return cached[0] if cached else None
    return school.subscriptions.filter(is_current=True).select_related('plan').first()


def directory_admins(school: School) -> list[SchoolMembership]:
    cached = getattr(school, 'admin_memberships', None)
    if cached is not None:
        return list(cached)
    return list(school_admin_memberships(school))


def active_staff_count(school: School) -> int:
    return SchoolMembership.objects.filter(school=school, is_active=True).count()


def active_student_count(school: School) -> int:
    return Student.objects.filter(school=school, is_active=True).count()


def _active_plan(code: str):
    from billing.models import Plan

    plan = Plan.objects.filter(code=code, is_active=True).first()
    if plan is None:
        raise ValidationError({'plan_code': 'Unknown or inactive plan.'})
    return plan


def _validate_addon(sku, *, channel: str, interval: str, plan, field: str) -> None:
    from communications.services.addons import validate_sku_for_subscription

    try:
        validate_sku_for_subscription(
            sku=sku,
            channel=channel,
            interval=interval,
            plan=plan,
        )
    except ValidationError as exc:
        message = exc.detail.get('sku') if isinstance(exc.detail, dict) else exc.detail
        raise ValidationError({field: message}) from exc


def _addon_sku(code: str, *, field: str):
    from communications.models import CommunicationAddonSku

    sku = CommunicationAddonSku.objects.filter(code=code).first()
    if sku is None:
        raise ValidationError({field: 'Unknown add-on.'})
    return sku


@transaction.atomic
def create_school_for_platform(
    *,
    actor: PlatformUser,
    name: str,
    phone_number: str,
    email: str | None = None,
    address: str | None = None,
    region: str = '',
    category: str = '',
    phone_number_alt: str | None = None,
    plan_code: str | None = None,
    interval: str | None = None,
    sms_sku_code: str | None = None,
    email_sku_code: str | None = None,
    ip_address: str | None = None,
) -> School:
    school = _provision_school(
        name=name.strip(),
        phone_number=phone_number.strip(),
        status=School.Status.PENDING,
        email=(email or '').strip() or None,
        address=(address or '').strip() or None,
        region=(region or '').strip(),
        category=(category or '').strip(),
        phone_number_alt=(phone_number_alt or '').strip() or None,
    )
    chosen_plan = (plan_code or '').strip()
    chosen_interval = (interval or '').strip()
    if chosen_plan:
        from billing.services.subscriptions import start_subscription

        plan = _active_plan(chosen_plan)
        sms_sku = (
            _addon_sku(sms_sku_code, field='sms_sku_code')
            if (sms_sku_code or '').strip()
            else None
        )
        email_sku = (
            _addon_sku(email_sku_code, field='email_sku_code')
            if (email_sku_code or '').strip()
            else None
        )
        if sms_sku is not None:
            _validate_addon(
                sms_sku,
                channel='sms',
                interval=chosen_interval,
                plan=plan,
                field='sms_sku_code',
            )
        if email_sku is not None:
            _validate_addon(
                email_sku,
                channel='email',
                interval=chosen_interval,
                plan=plan,
                field='email_sku_code',
            )
        start_subscription(
            school=school,
            plan=plan,
            interval=chosen_interval,
            apply_first_year_free=False,
            sms_sku=sms_sku,
            email_sku=email_sku,
            actor=actor,
            ip_address=ip_address,
        )
    else:
        from billing.services.migrate import ensure_complimentary_subscription

        ensure_complimentary_subscription(school)
    record_audit(
        actor=actor,
        action='platform.school.created',
        target_type='school',
        target_id=str(school.pk),
        detail={
            'name': school.name,
            'status': school.status,
            'plan_code': chosen_plan,
            'interval': chosen_interval,
        },
        ip_address=ip_address,
    )
    return school


@transaction.atomic
def update_school_for_platform(
    *,
    actor: PlatformUser,
    school: School,
    data: dict,
    ip_address: str | None = None,
) -> School:
    allowed = {
        'name',
        'phone_number',
        'phone_number_alt',
        'email',
        'address',
        'region',
        'category',
        'motto',
        'gps_address',
        'box_address',
    }
    updates = []
    for key, value in data.items():
        if key not in allowed:
            continue
        setattr(school, key, value)
        updates.append(key)
    if updates:
        school.save(update_fields=[*updates, 'updated_at'])
        record_audit(
            actor=actor,
            action='platform.school.updated',
            target_type='school',
            target_id=str(school.pk),
            detail={'fields': updates},
            ip_address=ip_address,
        )
    return school


@transaction.atomic
def set_school_status(
    *,
    actor: PlatformUser,
    school: School,
    status: str,
    ip_address: str | None = None,
) -> School:
    if status not in School.Status.values:
        raise ValidationError({'status': 'Invalid school status.'})
    if school.status == status:
        return school

    previous = school.status
    school.status = status
    fields = ['status', 'updated_at']
    now = timezone.now()
    if status == School.Status.ACTIVE:
        school.activated_at = school.activated_at or now
        school.suspended_at = None
        fields.extend(['activated_at', 'suspended_at'])
    elif status == School.Status.SUSPENDED:
        school.suspended_at = now
        fields.append('suspended_at')
    elif status == School.Status.PENDING:
        school.suspended_at = None
        fields.append('suspended_at')

    school.save(update_fields=fields)
    record_audit(
        actor=actor,
        action='platform.school.status_changed',
        target_type='school',
        target_id=str(school.pk),
        detail={'from': previous, 'to': status},
        ip_address=ip_address,
    )
    return school


def school_admin_memberships(school: School) -> QuerySet[SchoolMembership]:
    return (
        SchoolMembership.objects.filter(
            school=school,
            is_active=True,
            role=User.RoleChoices.ADMIN,
        )
        .select_related('user')
        .order_by('created_at')
    )
