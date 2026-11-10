from __future__ import annotations

from dataclasses import dataclass

from rest_framework.exceptions import ValidationError

from accounts.models import SchoolMembership
from billing.models import SchoolSubscription
from students.models import Student


STUDENT_CAPACITY_EXCEEDED_CODE = 'student_capacity_exceeded'
STAFF_CAPACITY_EXCEEDED_CODE = 'staff_capacity_exceeded'
# Backward-compatible alias
CAPACITY_EXCEEDED_CODE = STUDENT_CAPACITY_EXCEEDED_CODE


@dataclass(frozen=True)
class CapacitySnapshot:
    active_students: int
    capacity_max: int | None
    active_staff: int
    staff_capacity_max: int | None
    plan_code: str | None
    plan_name: str | None
    warnings: list[float]
    at_or_over_capacity: bool
    at_or_over_student_capacity: bool
    at_or_over_staff_capacity: bool
    usage_ratio: float | None
    staff_usage_ratio: float | None


def active_student_count(school) -> int:
    return Student.objects.filter(school=school, is_active=True).count()


def active_staff_count(school) -> int:
    return SchoolMembership.objects.filter(school=school, is_active=True).count()


def current_subscription(school) -> SchoolSubscription | None:
    return (
        SchoolSubscription.objects.filter(school=school, is_current=True)
        .select_related('plan')
        .first()
    )


def _warning_levels(plan) -> list[float]:
    warnings = []
    for raw in (plan.warning_thresholds or []):
        try:
            warnings.append(float(raw))
        except (TypeError, ValueError):
            continue
    return sorted({w for w in warnings if 0 < w <= 1})


def get_capacity_snapshot(school) -> CapacitySnapshot:
    subscription = current_subscription(school)
    students = active_student_count(school)
    staff = active_staff_count(school)
    if subscription is None:
        return CapacitySnapshot(
            active_students=students,
            capacity_max=None,
            active_staff=staff,
            staff_capacity_max=None,
            plan_code=None,
            plan_name=None,
            warnings=[],
            at_or_over_capacity=False,
            at_or_over_student_capacity=False,
            at_or_over_staff_capacity=False,
            usage_ratio=None,
            staff_usage_ratio=None,
        )

    plan = subscription.plan
    student_max = plan.student_max
    staff_max = plan.staff_max
    warnings = _warning_levels(plan)

    student_ratio = None
    staff_ratio = None
    over_students = False
    over_staff = False
    if student_max is not None and student_max > 0:
        student_ratio = students / student_max
        over_students = students >= student_max
    if staff_max is not None and staff_max > 0:
        staff_ratio = staff / staff_max
        over_staff = staff >= staff_max

    return CapacitySnapshot(
        active_students=students,
        capacity_max=student_max,
        active_staff=staff,
        staff_capacity_max=staff_max,
        plan_code=plan.code,
        plan_name=plan.name,
        warnings=warnings,
        at_or_over_capacity=over_students or over_staff,
        at_or_over_student_capacity=over_students,
        at_or_over_staff_capacity=over_staff,
        usage_ratio=student_ratio,
        staff_usage_ratio=staff_ratio,
    )


def ensure_can_add_students(school, *, additional: int = 1) -> CapacitySnapshot:
    """Block when adding ``additional`` active students would exceed plan max."""
    snapshot = get_capacity_snapshot(school)
    if snapshot.capacity_max is None:
        return snapshot

    projected = snapshot.active_students + max(0, additional)
    if projected > snapshot.capacity_max:
        raise ValidationError(
            {
                'detail': (
                    f'Student capacity reached for plan {snapshot.plan_name} '
                    f'({snapshot.active_students}/{snapshot.capacity_max}). '
                    'Upgrade the subscription before adding or reactivating students.'
                ),
                'code': STUDENT_CAPACITY_EXCEEDED_CODE,
                'active_students': snapshot.active_students,
                'capacity_max': snapshot.capacity_max,
                'plan_code': snapshot.plan_code,
            },
        )
    return snapshot


def ensure_can_add_staff(school, *, additional: int = 1) -> CapacitySnapshot:
    """Block when adding ``additional`` active staff seats would exceed plan max."""
    snapshot = get_capacity_snapshot(school)
    if snapshot.staff_capacity_max is None:
        return snapshot

    projected = snapshot.active_staff + max(0, additional)
    if projected > snapshot.staff_capacity_max:
        raise ValidationError(
            {
                'detail': (
                    f'Staff capacity reached for plan {snapshot.plan_name} '
                    f'({snapshot.active_staff}/{snapshot.staff_capacity_max}). '
                    'Upgrade the subscription before adding or reactivating staff.'
                ),
                'code': STAFF_CAPACITY_EXCEEDED_CODE,
                'active_staff': snapshot.active_staff,
                'staff_capacity_max': snapshot.staff_capacity_max,
                'plan_code': snapshot.plan_code,
            },
        )
    return snapshot


def triggered_warning_levels(snapshot: CapacitySnapshot) -> list[float]:
    ratios = [
        ratio
        for ratio in (snapshot.usage_ratio, snapshot.staff_usage_ratio)
        if ratio is not None
    ]
    if not ratios:
        return []
    peak = max(ratios)
    return [level for level in snapshot.warnings if peak >= level]
