from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from billing.models import SchoolSubscription
from billing.services.capacity import current_subscription
from communications.services.ledger import get_balances, get_or_create_account
from communications.services.segments import units_for_channel


@dataclass(frozen=True)
class SendEligibility:
    allowed: bool
    reason: str = ''
    balance: int = 0
    required: int = 0
    billing_active: bool = True


def communications_billing_active(school) -> bool:
    """Guardian messaging always meters credits (no legacy free path)."""
    return True


def subscription_allows_sends(subscription: SchoolSubscription | None) -> SendEligibility:
    if subscription is None:
        # Still allow credit-gated sends for schools without a subscription row.
        return SendEligibility(True, billing_active=True)
    if subscription.status == SchoolSubscription.Status.ACTIVE:
        return SendEligibility(True, billing_active=True)
    if subscription.status == SchoolSubscription.Status.PAST_DUE:
        grace_end = subscription.grace_period_ends_at
        if grace_end is None or grace_end >= timezone.now():
            return SendEligibility(True, billing_active=True)
        return SendEligibility(False, 'past_due_grace_expired', billing_active=True)
    return SendEligibility(False, f'subscription_{subscription.status}', billing_active=True)


def school_allows_sends(school) -> SendEligibility:
    if hasattr(school, 'is_accessible') and not school.is_accessible:
        return SendEligibility(False, 'school_inaccessible', billing_active=True)
    status = getattr(school, 'status', None)
    if status in {'suspended', 'archived'}:
        return SendEligibility(False, f'school_{status}', billing_active=True)
    return subscription_allows_sends(current_subscription(school))


def can_send_channel(
    school,
    *,
    channel: str,
    body: str = '',
    units: int | None = None,
) -> SendEligibility:
    base = school_allows_sends(school)
    if not base.allowed:
        return base

    required = units if units is not None else units_for_channel(channel=channel, body=body)
    account = get_or_create_account(school, channel)
    if account.balance < required:
        return SendEligibility(
            False,
            'insufficient_credits',
            balance=account.balance,
            required=required,
            billing_active=True,
        )
    return SendEligibility(
        True,
        balance=account.balance,
        required=required,
        billing_active=True,
    )


def filter_items_by_credits(school, channel: str, items: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split items into (sendable, skipped) based on running credit balance.

    Does not debit — caller debits after successful provider send.
    """
    eligibility = school_allows_sends(school)
    if not eligibility.allowed:
        return [], [
            {**item, 'skip_reason': eligibility.reason}
            for item in items
        ]

    balances = get_balances(school)
    remaining = balances.get(channel, 0)
    sendable: list[dict] = []
    skipped: list[dict] = []
    for item in items:
        body = item.get('body') or item.get('text_body') or ''
        units = units_for_channel(channel=channel, body=body)
        if remaining < units:
            skipped.append({
                **item,
                'skip_reason': 'insufficient_credits',
                'units': units,
                'billable': True,
            })
            continue
        remaining -= units
        sendable.append({**item, 'units': units, 'billable': True})
    return sendable, skipped
