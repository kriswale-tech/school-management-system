"""Resolve platform discounts when a subscription invoice is opened.

A discount covers billing months, not whole invoices. An annual invoice that
overlaps six months of a "first six months" offer is reduced by half of the
percent. One discount is written per invoice; the larger cedi saving wins.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from billing.models import (
    InvoiceLine,
    PromotionCampaign,
    PromotionRedemption,
    SchoolSubscription,
    SubscriptionPeriod,
)
from billing.services.catalog import FIRST_YEAR_FREE_CODE
from billing.services.period import add_billing_interval

_CENTS = Decimal('0.01')
_APPLICATION_KINDS = {
    InvoiceLine.Kind.APPLICATION,
    InvoiceLine.Kind.APPLICATION_PRORATION,
}
_COMMUNICATION_KINDS = {
    InvoiceLine.Kind.SMS_ADDON,
    InvoiceLine.Kind.EMAIL_ADDON,
}


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_CENTS)


def _add_months(start: datetime, months: int) -> datetime:
    cursor = start
    for _ in range(max(int(months), 0)):
        cursor = add_billing_interval(cursor, SchoolSubscription.Interval.MONTHLY)
    return cursor


def interval_month_count(interval: str) -> int:
    if interval == SchoolSubscription.Interval.ANNUAL:
        return 12
    return 1


def school_billing_origin(school, *, fallback: datetime) -> datetime:
    """When this school's paid service began. Introductory windows count from here."""
    earliest_period = (
        SubscriptionPeriod.objects.filter(subscription__school=school)
        .order_by('starts_at')
        .values_list('starts_at', flat=True)
        .first()
    )
    if earliest_period is not None:
        return earliest_period
    earliest_subscription = (
        SchoolSubscription.objects.filter(school=school)
        .order_by('created_at')
        .values_list('current_period_start', flat=True)
        .first()
    )
    return earliest_subscription or fallback


def is_first_subscription(subscription: SchoolSubscription) -> bool:
    first_id = (
        SchoolSubscription.objects.filter(school_id=subscription.school_id)
        .order_by('created_at', 'id')
        .values_list('id', flat=True)
        .first()
    )
    return first_id == subscription.id


def month_starts(origin: datetime, count: int) -> list[datetime]:
    cursor = origin
    starts: list[datetime] = []
    for _ in range(count):
        starts.append(cursor)
        cursor = add_billing_interval(cursor, SchoolSubscription.Interval.MONTHLY)
    return starts


def covered_month_starts(
    *,
    period_origin: datetime,
    period_end: datetime,
    interval: str,
    charge_start: datetime,
    charge_end: datetime,
) -> list[datetime]:
    """Billing months of this period that the invoice is actually charging for."""
    count = interval_month_count(interval)
    starts = month_starts(period_origin, count)
    covered: list[datetime] = []
    for index, step in enumerate(starts):
        step_end = starts[index + 1] if index + 1 < count else period_end
        if step < charge_end and step_end > charge_start:
            covered.append(step)
    return covered


def qualifying_month_counts(
    *,
    covered: list[datetime],
    benefit_start: datetime,
    benefit_end: datetime | None,
) -> tuple[int, int]:
    """Return (qualified months, covered months). A month qualifies when it starts inside the window."""
    qualified = 0
    for step in covered:
        if step < benefit_start:
            continue
        if benefit_end is not None and step >= benefit_end:
            continue
        qualified += 1
    return qualified, len(covered)


def _line_amount(line: dict) -> Decimal:
    return _quantize(Decimal(str(line['amount_ghs'])))


def _line_is_eligible(kind: str, applies_to: str) -> bool:
    if applies_to == PromotionCampaign.AppliesTo.ALL:
        return kind in _APPLICATION_KINDS or kind in _COMMUNICATION_KINDS
    if applies_to == PromotionCampaign.AppliesTo.COMMUNICATION:
        return kind in _COMMUNICATION_KINDS
    return kind in _APPLICATION_KINDS


def _eligible_base(lines: list[dict], applies_to: str) -> Decimal:
    total = Decimal('0.00')
    for line in lines:
        if line.get('kind') == InvoiceLine.Kind.DISCOUNT:
            continue
        if _line_is_eligible(line.get('kind', ''), applies_to):
            total += _line_amount(line)
    return _quantize(total)


def _campaign_window(campaign: PromotionCampaign, origin: datetime) -> tuple[datetime, datetime | None]:
    if campaign.schedule == PromotionCampaign.Schedule.DATE_RANGE:
        return campaign.starts_at, campaign.ends_at
    if campaign.schedule == PromotionCampaign.Schedule.RECURRING:
        return origin, None
    return origin, _add_months(origin, campaign.duration_months)


def _school_is_selected(campaign: PromotionCampaign, school_id) -> bool:
    selected = getattr(campaign, '_selected_school_ids', None)
    if selected is None:
        selected = set(campaign.schools.values_list('id', flat=True))
        campaign._selected_school_ids = selected
    return school_id in selected


def _can_enroll(
    campaign: PromotionCampaign,
    subscription: SchoolSubscription,
    *,
    interval: str,
    apply_first_year_free: bool,
) -> bool:
    if not campaign.is_active:
        return False
    if campaign.code == FIRST_YEAR_FREE_CODE and not apply_first_year_free:
        return False
    if campaign.billing_interval and campaign.billing_interval != interval:
        return False
    if campaign.audience == PromotionCampaign.Audience.NEW and not is_first_subscription(subscription):
        return False
    if campaign.audience == PromotionCampaign.Audience.SELECTED and not _school_is_selected(
        campaign,
        subscription.school_id,
    ):
        return False
    if campaign.schedule == PromotionCampaign.Schedule.INTRODUCTORY and campaign.duration_months < 1:
        return False
    if campaign.schedule == PromotionCampaign.Schedule.DATE_RANGE:
        if campaign.starts_at is None or campaign.ends_at is None:
            return False
        if campaign.ends_at <= campaign.starts_at:
            return False
    return True


@dataclass
class _Candidate:
    redemption: PromotionRedemption
    saving: Decimal
    qualified: int
    covered: int
    pending_create: bool


def _candidate_for_redemption(
    redemption: PromotionRedemption,
    *,
    lines: list[dict],
    period_origin: datetime,
    period_end: datetime,
    charge_start: datetime,
    charge_end: datetime,
    interval: str,
    pending_create: bool,
) -> _Candidate | None:
    if redemption.billing_interval and redemption.billing_interval != interval:
        return None
    if redemption.schedule == PromotionCampaign.Schedule.RECURRING and not redemption.campaign.is_active:
        return None
    covered = covered_month_starts(
        period_origin=period_origin,
        period_end=period_end,
        interval=interval,
        charge_start=charge_start,
        charge_end=charge_end,
    )
    qualified, total = qualifying_month_counts(
        covered=covered,
        benefit_start=redemption.starts_at,
        benefit_end=redemption.ends_at,
    )
    if qualified < 1 or total < 1:
        return None
    base = _eligible_base(lines, redemption.applies_to)
    if base <= 0:
        return None
    saving = _quantize(base * redemption.discount_percent / Decimal('100') * Decimal(qualified) / Decimal(total))
    if saving <= 0:
        return None
    return _Candidate(
        redemption=redemption,
        saving=saving,
        qualified=qualified,
        covered=total,
        pending_create=pending_create,
    )


def _discount_line(candidate: _Candidate) -> dict:
    redemption = candidate.redemption
    percent = redemption.discount_percent
    if candidate.qualified == candidate.covered:
        description = f'{redemption.campaign.name} ({percent}% off)'
    else:
        description = (
            f'{redemption.campaign.name} ({percent}% off, '
            f'{candidate.qualified} of {candidate.covered} months)'
        )
    return {
        'kind': InvoiceLine.Kind.DISCOUNT,
        'description': description[:255],
        'quantity': '1',
        'unit_price_ghs': str(candidate.saving),
        'amount_ghs': str(candidate.saving),
        'metadata': {
            'campaign_code': redemption.campaign.code,
            'campaign_id': str(redemption.campaign_id),
            'discount_percent': str(percent),
            'qualified_months': candidate.qualified,
            'covered_months': candidate.covered,
            'schedule': redemption.schedule,
        },
    }


@transaction.atomic
def apply_subscription_discount(
    lines: list[dict],
    *,
    subscription: SchoolSubscription,
    period_start: datetime,
    period_end: datetime,
    period_origin: datetime | None = None,
    interval: str | None = None,
    apply_first_year_free: bool = False,
    persist: bool = True,
) -> tuple[list[dict], PromotionRedemption | None]:
    """Append at most one discount line. Paid lines are left unchanged.

    ``period_origin`` is the start of the billing period being split into months.
    Pass the subscription period start for a mid-period upgrade, whose invoice
    only charges the remainder. Previews pass ``persist=False``.
    """
    priced = [line for line in lines if line.get('kind') != InvoiceLine.Kind.DISCOUNT]
    interval = interval or subscription.interval
    origin = school_billing_origin(subscription.school, fallback=period_start)
    anchor = period_origin or period_start

    existing = {
        redemption.campaign_id: redemption
        for redemption in PromotionRedemption.objects.filter(
            school_id=subscription.school_id,
        ).select_related('campaign')
    }
    active_campaigns = list(
        PromotionCampaign.objects.filter(is_active=True).prefetch_related('schools'),
    )
    campaigns_by_id = {campaign.id: campaign for campaign in active_campaigns}
    for redemption in existing.values():
        campaigns_by_id.setdefault(redemption.campaign_id, redemption.campaign)

    candidates: list[_Candidate] = []
    for campaign in campaigns_by_id.values():
        redemption = existing.get(campaign.id)
        pending_create = False
        if redemption is not None:
            if redemption.revoked_at is not None:
                continue
        else:
            if not _can_enroll(
                campaign,
                subscription,
                interval=interval,
                apply_first_year_free=apply_first_year_free,
            ):
                continue
            benefit_start, benefit_end = _campaign_window(campaign, origin)
            if benefit_start is None:
                continue
            redemption = PromotionRedemption(
                school=subscription.school,
                campaign=campaign,
                subscription=subscription,
                starts_at=benefit_start,
                ends_at=benefit_end,
                discount_percent=campaign.discount_percent,
                applies_to=campaign.applies_to,
                schedule=campaign.schedule,
                billing_interval=campaign.billing_interval or '',
            )
            pending_create = True

        candidate = _candidate_for_redemption(
            redemption,
            lines=priced,
            period_origin=anchor,
            period_end=period_end,
            charge_start=period_start,
            charge_end=period_end,
            interval=interval,
            pending_create=pending_create,
        )
        if candidate is not None:
            candidates.append(candidate)

    if not candidates:
        return priced, None

    winner = max(
        candidates,
        key=lambda item: (
            item.saving,
            item.redemption.discount_percent,
            -item.redemption.campaign.created_at.timestamp(),
        ),
    )
    if persist:
        for candidate in candidates:
            if not candidate.pending_create:
                continue
            redemption = candidate.redemption
            PromotionRedemption.objects.get_or_create(
                school=redemption.school,
                campaign=redemption.campaign,
                defaults={
                    'subscription': redemption.subscription,
                    'starts_at': redemption.starts_at,
                    'ends_at': redemption.ends_at,
                    'discount_percent': redemption.discount_percent,
                    'applies_to': redemption.applies_to,
                    'schedule': redemption.schedule,
                    'billing_interval': redemption.billing_interval,
                },
            )
        stored = PromotionRedemption.objects.filter(
            school_id=subscription.school_id,
            campaign_id=winner.redemption.campaign_id,
        ).select_related('campaign').first()
        if stored is not None:
            winner.redemption = stored

    priced.append(_discount_line(winner))
    return priced, winner.redemption


def subscription_discount_summaries(subscription: SchoolSubscription) -> list[dict]:
    """Discounts still able to reduce a future invoice for this school."""
    now = timezone.now()
    rows = []
    redemptions = (
        PromotionRedemption.objects.filter(
            school_id=subscription.school_id,
            revoked_at__isnull=True,
        )
        .select_related('campaign')
        .order_by('starts_at')
    )
    for redemption in redemptions:
        if redemption.ends_at is not None and redemption.ends_at <= now:
            continue
        if (
            redemption.schedule == PromotionCampaign.Schedule.RECURRING
            and not redemption.campaign.is_active
        ):
            continue
        rows.append({
            'id': str(redemption.pk),
            'campaign_id': str(redemption.campaign_id),
            'code': redemption.campaign.code,
            'name': redemption.campaign.name,
            'discount_percent': str(redemption.discount_percent),
            'schedule': redemption.schedule,
            'applies_to': redemption.applies_to,
            'starts_at': redemption.starts_at,
            'ends_at': redemption.ends_at,
        })
    return rows
