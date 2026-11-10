"""Free / sponsored classification for outbound guardian traffic (v4.1 §2.10, §2.11).

Default behaviour is unchanged from v4: with no allowance policy configured,
guardian traffic classifies as ``paid``. v4.1 introduces no free messaging by
default. Consumption is counted from classified delivery rows — there is no
second wallet and no ledger entry for free or sponsored sends.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from communications.models import MessagingAllowancePolicy
from communications.services.ranges import day_window, month_window

logger = logging.getLogger(__name__)

PAID = 'paid'


@dataclass
class AllowanceBudget:
    """Mutable remaining-units view for one policy inside one batch."""

    policy: MessagingAllowancePolicy
    monthly_remaining: int
    daily_remaining: int | None
    budget_remaining_ghs: Decimal | None

    @property
    def classification(self) -> str:
        return self.policy.classification

    def has_room(self, units: int) -> bool:
        if self.monthly_remaining < units:
            return False
        if self.daily_remaining is not None and self.daily_remaining < units:
            return False
        if self.budget_remaining_ghs is not None and self.budget_remaining_ghs <= 0:
            return False
        return True

    def consume(self, units: int, *, cost_ghs: Decimal | None = None) -> None:
        self.monthly_remaining = max(0, self.monthly_remaining - units)
        if self.daily_remaining is not None:
            self.daily_remaining = max(0, self.daily_remaining - units)
        if self.budget_remaining_ghs is not None and cost_ghs is not None:
            self.budget_remaining_ghs = self.budget_remaining_ghs - cost_ghs


def _scope_filter(school) -> Q:
    return Q(scope=MessagingAllowancePolicy.Scope.PLATFORM, school__isnull=True) | Q(
        scope=MessagingAllowancePolicy.Scope.SCHOOL,
        school=school,
    )


def active_policies(*, school, channel: str, moment=None) -> list[MessagingAllowancePolicy]:
    """Policies in force for this school and channel — school scope wins first."""
    now = moment or timezone.now()
    rows = list(
        MessagingAllowancePolicy.objects.filter(
            channel=channel,
            is_active=True,
            starts_at__lte=now,
        )
        .filter(_scope_filter(school))
        .exclude(ends_at__lt=now),
    )
    rows.sort(
        key=lambda policy: (
            0 if policy.scope == MessagingAllowancePolicy.Scope.SCHOOL else 1,
            policy.name,
        ),
    )
    return rows


def consumed_units(*, policy: MessagingAllowancePolicy, start, end) -> int:
    """Units already consumed against ``policy`` in ``[start, end)``."""
    from notifications.models import GuardianDelivery

    qs = GuardianDelivery.objects.filter(
        allowance=policy,
        created_at__gte=start,
        created_at__lt=end,
    ).exclude(status=GuardianDelivery.Status.SKIPPED)
    aggregate = qs.aggregate(segments=Sum('segments'), rows=Count('id'))
    if policy.channel == MessagingAllowancePolicy.Channel.SMS:
        return int(aggregate['segments'] or 0)
    return int(aggregate['rows'] or 0)


def consumed_cost_ghs(*, policy: MessagingAllowancePolicy, start, end) -> Decimal:
    """Provider cost already absorbed under ``policy`` in ``[start, end)``."""
    from notifications.models import GuardianDelivery

    total = (
        GuardianDelivery.objects.filter(
            allowance=policy,
            created_at__gte=start,
            created_at__lt=end,
        )
        .exclude(status=GuardianDelivery.Status.SKIPPED)
        .aggregate(cost=Sum('provider_cost_snapshot_ghs'))['cost']
    )
    return Decimal(total or 0)


def build_budget(policy: MessagingAllowancePolicy, *, moment=None) -> AllowanceBudget:
    month_start, month_end = month_window(moment)
    monthly_used = consumed_units(policy=policy, start=month_start, end=month_end)
    monthly_remaining = max(0, int(policy.monthly_free_units or 0) - monthly_used)

    daily_remaining = None
    if policy.daily_limit_units is not None:
        day_start, day_end = day_window(moment)
        daily_used = consumed_units(policy=policy, start=day_start, end=day_end)
        daily_remaining = max(0, int(policy.daily_limit_units) - daily_used)

    budget_remaining = None
    if policy.budget_ghs is not None:
        window_start = policy.starts_at
        window_end = policy.ends_at or timezone.now()
        spent = consumed_cost_ghs(policy=policy, start=window_start, end=window_end)
        budget_remaining = Decimal(policy.budget_ghs) - spent

    return AllowanceBudget(
        policy=policy,
        monthly_remaining=monthly_remaining,
        daily_remaining=daily_remaining,
        budget_remaining_ghs=budget_remaining,
    )


def allowance_status(policy: MessagingAllowancePolicy, *, moment=None) -> dict:
    """Read-only consumption view used by the free & sponsored dashboards."""
    budget = build_budget(policy, moment=moment)
    monthly_total = int(policy.monthly_free_units or 0)
    used = max(0, monthly_total - budget.monthly_remaining)
    fraction = (used / monthly_total) if monthly_total else 0.0
    thresholds = [
        float(value)
        for value in (policy.alert_thresholds or [])
        if isinstance(value, (int, float))
    ]
    return {
        'monthly_free_units': monthly_total,
        'monthly_used_units': used,
        'monthly_remaining_units': budget.monthly_remaining,
        'daily_limit_units': policy.daily_limit_units,
        'daily_remaining_units': budget.daily_remaining,
        'budget_ghs': str(policy.budget_ghs) if policy.budget_ghs is not None else None,
        'budget_remaining_ghs': (
            str(budget.budget_remaining_ghs)
            if budget.budget_remaining_ghs is not None
            else None
        ),
        'consumed_fraction': round(fraction, 4),
        'alerts_triggered': sorted(
            threshold for threshold in thresholds if fraction >= threshold
        ),
        'exhausted': not budget.has_room(1),
    }


def resolve_classification(
    *,
    school,
    channel: str,
    event_type: str,
    units: int = 1,
    budgets: dict | None = None,
    moment=None,
) -> tuple[str, MessagingAllowancePolicy | None, str]:
    """Classify one send as ``paid`` / ``free`` / ``sponsored``.

    ``budgets`` is an optional per-batch cache keyed by policy id so a batch of
    100 items does not re-count consumption 100 times. Returns
    ``(classification, policy, reason)``; ``reason`` explains a paid fallback.
    """
    cache = budgets if budgets is not None else {}
    policies = cache.get('__policies__')
    if policies is None:
        policies = active_policies(school=school, channel=channel, moment=moment)
        cache['__policies__'] = policies

    exhausted_skip = False
    for policy in policies:
        if not policy.covers_event(event_type):
            continue
        budget = cache.get(policy.pk)
        if budget is None:
            budget = build_budget(policy, moment=moment)
            cache[policy.pk] = budget
        if budget.has_room(units):
            return policy.classification, policy, 'allowance'
        if policy.exhausted_behavior == MessagingAllowancePolicy.ExhaustedBehavior.SKIP:
            exhausted_skip = True

    if exhausted_skip:
        return PAID, None, 'allowance_exhausted_skip'
    return PAID, None, 'no_allowance'


def classify_items(
    *,
    school,
    channel: str,
    items: list[dict],
    moment=None,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Split items into (paid, free_or_sponsored, skipped) with classification set.

    ``billable=False`` on free/sponsored items means the school ledger is never
    touched for them. Items whose only matching policy is exhausted and
    configured to skip land in ``skipped`` with an explicit reason rather than
    being silently charged instead.
    """
    from communications.services.pricing import snapshot_for_channel
    from communications.services.segments import units_for_channel

    budgets: dict = {}
    paid: list[dict] = []
    covered: list[dict] = []
    skipped: list[dict] = []

    for item in items:
        body = item.get('body') or item.get('text_body') or ''
        units = int(item.get('units') or 0) or units_for_channel(channel=channel, body=body)

        classification, policy, reason = resolve_classification(
            school=school,
            channel=channel,
            event_type=item.get('event_type') or '',
            units=units,
            budgets=budgets,
            moment=moment,
        )

        row = {**item, 'units': units, 'billing_classification': classification}
        if classification == PAID:
            row['billable'] = True
            row['allowance_id'] = None
            if reason == 'allowance_exhausted_skip':
                skipped.append({**row, 'skip_reason': 'allowance_exhausted'})
            else:
                paid.append(row)
            continue

        row['billable'] = False
        row['allowance_id'] = str(policy.pk) if policy else None
        snapshot = snapshot_for_channel(channel=channel, body=body, units=units)
        cost = snapshot.get('provider_cost_snapshot_ghs')
        budget = budgets.get(policy.pk) if policy else None
        if budget is not None:
            budget.consume(units, cost_ghs=Decimal(cost) if cost is not None else None)
        covered.append(row)

    return paid, covered, skipped
