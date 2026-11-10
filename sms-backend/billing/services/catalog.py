from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from billing.models import Plan, PromotionCampaign


DEFAULT_PLANS = [
    {
        'code': 'starter',
        'name': 'Starter',
        'student_min': 1,
        'student_max': 100,
        'staff_min': 1,
        'staff_max': 10,
        'price_monthly_ghs': Decimal('80.00'),
        'price_annual_ghs': Decimal('800.00'),
        'warning_thresholds': [0.8, 0.95],
        'sort_order': 1,
    },
    {
        'code': 'basic',
        'name': 'Basic',
        'student_min': 101,
        'student_max': 300,
        'staff_min': 1,
        'staff_max': 25,
        'price_monthly_ghs': Decimal('150.00'),
        'price_annual_ghs': Decimal('1500.00'),
        'warning_thresholds': [0.8, 0.95],
        'sort_order': 2,
    },
    {
        'code': 'standard',
        'name': 'Standard',
        'student_min': 301,
        'student_max': 600,
        'staff_min': 1,
        'staff_max': 50,
        'price_monthly_ghs': Decimal('250.00'),
        'price_annual_ghs': Decimal('2400.00'),
        'warning_thresholds': [0.8, 0.95],
        'sort_order': 3,
    },
    {
        'code': 'premium',
        'name': 'Premium',
        'student_min': 601,
        'student_max': 1000,
        'staff_min': 1,
        'staff_max': 80,
        'price_monthly_ghs': Decimal('400.00'),
        'price_annual_ghs': Decimal('4000.00'),
        'warning_thresholds': [0.8, 0.95],
        'sort_order': 4,
    },
    {
        'code': 'enterprise',
        'name': 'Enterprise',
        'student_min': 1001,
        'student_max': None,
        'staff_min': 1,
        'staff_max': None,
        'price_monthly_ghs': Decimal('600.00'),
        'price_annual_ghs': Decimal('6000.00'),
        'warning_thresholds': [0.8, 0.95],
        'sort_order': 5,
    },
]

FIRST_YEAR_FREE_CODE = 'first_year_free'


@transaction.atomic
def seed_default_plans() -> list[Plan]:
    plans = []
    for row in DEFAULT_PLANS:
        plan, _ = Plan.objects.update_or_create(
            code=row['code'],
            defaults={
                'name': row['name'],
                'student_min': row['student_min'],
                'student_max': row['student_max'],
                'staff_min': row['staff_min'],
                'staff_max': row['staff_max'],
                'price_monthly_ghs': row['price_monthly_ghs'],
                'price_annual_ghs': row['price_annual_ghs'],
                'warning_thresholds': row['warning_thresholds'],
                'sort_order': row['sort_order'],
                'is_active': True,
            },
        )
        plans.append(plan)
    return plans


@transaction.atomic
def seed_first_year_free_campaign() -> PromotionCampaign:
    campaign, _ = PromotionCampaign.objects.update_or_create(
        code=FIRST_YEAR_FREE_CODE,
        defaults={
            'name': 'First year complimentary',
            'discount_percent': Decimal('100.00'),
            'applies_to': PromotionCampaign.AppliesTo.APPLICATION,
            'schedule': PromotionCampaign.Schedule.INTRODUCTORY,
            'audience': PromotionCampaign.Audience.NEW,
            'billing_interval': '',
            'duration_months': 12,
            'is_active': True,
            'first_subscription_only': True,
        },
    )
    return campaign


def plan_for_student_count(count: int) -> Plan:
    """Backward-compatible helper — prefers student band, then staff-open."""
    return plan_for_usage(students=count, staff=0)


def plan_for_usage(*, students: int, staff: int) -> Plan:
    """Lowest active plan that can host both student and staff counts."""
    students = max(int(students), 0)
    staff = max(int(staff), 0)
    qs = Plan.objects.filter(is_active=True).order_by('sort_order', 'student_min')

    if students == 0 and staff == 0:
        starter = qs.filter(code='starter').first()
        if starter is not None:
            return starter

    # Prefer the student-band plan when staff also fits; otherwise bump tiers.
    band_plan = None
    for plan in qs:
        if students == 0 or plan.covers_student_count(max(students, 1)):
            band_plan = plan
            break
    if band_plan is not None and band_plan.covers_usage(students=students, staff=staff):
        return band_plan

    for plan in qs:
        if plan.covers_usage(students=students, staff=staff):
            return plan

    enterprise = qs.filter(student_max__isnull=True, staff_max__isnull=True).order_by(
        '-sort_order',
    ).first()
    if enterprise is not None:
        return enterprise
    raise Plan.DoesNotExist('No active billing plans configured.')


def next_higher_plan(plan: Plan) -> Plan | None:
    return (
        Plan.objects.filter(is_active=True, sort_order__gt=plan.sort_order)
        .order_by('sort_order')
        .first()
    )


def next_plan_covering_usage(
    *,
    current: Plan,
    students: int,
    staff: int,
) -> Plan | None:
    """Next higher tier that fits current student + staff usage."""
    qs = (
        Plan.objects.filter(is_active=True, sort_order__gt=current.sort_order)
        .order_by('sort_order')
    )
    for plan in qs:
        if plan.covers_usage(students=students, staff=staff):
            return plan
    return None
