from __future__ import annotations

from django.db import transaction

from billing.models import SchoolSubscription
from billing.services.catalog import seed_default_plans, seed_first_year_free_campaign
from billing.services.subscriptions import start_subscription
from schools.models import School


@transaction.atomic
def ensure_catalog() -> None:
    seed_default_plans()
    seed_first_year_free_campaign()


def ensure_complimentary_subscription(school) -> SchoolSubscription | None:
    """Start a first-year-free annual subscription if the school has none yet.

    Safe to call repeatedly — returns the existing current subscription when present.
    No-ops (returns None) when the plan catalog has not been seeded yet.
    """
    existing = SchoolSubscription.objects.filter(school=school, is_current=True).first()
    if existing is not None:
        return existing
    from billing.models import Plan

    if not Plan.objects.filter(is_active=True).exists():
        return None
    return start_subscription(
        school=school,
        interval=SchoolSubscription.Interval.ANNUAL,
        apply_first_year_free=True,
        actor=None,
    )


def migrate_existing_schools(*, dry_run: bool = False) -> dict:
    """Attach complimentary first-year subscriptions to schools that lack one."""
    from django.db.models import Exists, OuterRef

    ensure_catalog()
    has_current = SchoolSubscription.objects.filter(
        school_id=OuterRef('pk'),
        is_current=True,
    )
    schools = (
        School.objects.annotate(_has_current=Exists(has_current))
        .filter(_has_current=False)
        .order_by('created_at')
    )
    created = 0
    school_ids: list[str] = []
    for school in schools.iterator():
        if dry_run:
            created += 1
            school_ids.append(str(school.pk))
            continue
        start_subscription(
            school=school,
            interval=SchoolSubscription.Interval.ANNUAL,
            apply_first_year_free=True,
            actor=None,
        )
        created += 1
        school_ids.append(str(school.pk))
    skipped = School.objects.annotate(_has_current=Exists(has_current)).filter(
        _has_current=True,
    ).count()
    return {
        'created': created,
        'skipped': skipped,
        'dry_run': dry_run,
        'school_ids': school_ids,
    }
