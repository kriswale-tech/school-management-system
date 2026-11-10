from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from communications.models import CreditAccount, CreditLedgerEntry

INSUFFICIENT_CREDITS_CODE = 'insufficient_communication_credits'


class InsufficientCredits(ValidationError):
    default_detail = {
        'detail': 'Insufficient communication credits.',
        'code': INSUFFICIENT_CREDITS_CODE,
    }


def get_or_create_account(school, channel: str) -> CreditAccount:
    account, _ = CreditAccount.objects.get_or_create(
        school=school,
        channel=channel,
        defaults={'balance': 0},
    )
    return account


def get_balances(school) -> dict[str, int]:
    accounts = CreditAccount.objects.filter(school=school)
    balances = {
        CreditAccount.Channel.SMS: 0,
        CreditAccount.Channel.EMAIL: 0,
    }
    for account in accounts:
        balances[account.channel] = account.balance
    return balances


@transaction.atomic
def write_ledger_entry(
    *,
    school,
    channel: str,
    entry_type: str,
    delta: int,
    idempotency_key: str,
    subscription_period=None,
    invoice=None,
    guardian_delivery=None,
    actor_platform_user=None,
    metadata: dict | None = None,
    allow_negative: bool = False,
    occurred_at=None,
) -> CreditLedgerEntry:
    """Append a ledger row and update the cached balance.

    Idempotent on ``idempotency_key`` — returns the existing row if already written.
    """
    existing = CreditLedgerEntry.objects.filter(idempotency_key=idempotency_key).first()
    if existing is not None:
        return existing

    account = (
        CreditAccount.objects.select_for_update()
        .filter(school=school, channel=channel)
        .first()
    )
    if account is None:
        account = CreditAccount.objects.create(school=school, channel=channel, balance=0)
        account = CreditAccount.objects.select_for_update().get(pk=account.pk)

    new_balance = account.balance + delta
    if new_balance < 0 and not allow_negative:
        raise InsufficientCredits({
            'detail': (
                f'Insufficient {channel} credits '
                f'(have {account.balance}, need {abs(delta)}).'
            ),
            'code': INSUFFICIENT_CREDITS_CODE,
            'channel': channel,
            'balance': account.balance,
            'required': abs(delta),
        })

    account.balance = new_balance
    account.save(update_fields=['balance', 'updated_at'])

    try:
        return CreditLedgerEntry.objects.create(
            school=school,
            channel=channel,
            entry_type=entry_type,
            delta=delta,
            balance_after=new_balance,
            idempotency_key=idempotency_key,
            occurred_at=occurred_at or timezone.now(),
            subscription_period=subscription_period,
            invoice=invoice,
            guardian_delivery=guardian_delivery,
            actor_platform_user=actor_platform_user,
            metadata=metadata or {},
        )
    except IntegrityError:
        return CreditLedgerEntry.objects.get(idempotency_key=idempotency_key)


def allocate_recurring(
    *,
    school,
    channel: str,
    credits: int,
    period,
    invoice=None,
    metadata: dict | None = None,
) -> CreditLedgerEntry | None:
    if credits <= 0:
        return None
    return write_ledger_entry(
        school=school,
        channel=channel,
        entry_type=CreditLedgerEntry.EntryType.ALLOCATION_RECURRING,
        delta=credits,
        idempotency_key=f'alloc:{school.pk}:{channel}:{period.pk}',
        subscription_period=period,
        invoice=invoice,
        metadata={
            'credits': credits,
            **(metadata or {}),
        },
    )


def grant_topup(
    *,
    school,
    channel: str,
    credits: int,
    idempotency_key: str,
    invoice=None,
    metadata: dict | None = None,
) -> CreditLedgerEntry | None:
    if credits <= 0:
        return None
    return write_ledger_entry(
        school=school,
        channel=channel,
        entry_type=CreditLedgerEntry.EntryType.TOPUP,
        delta=credits,
        idempotency_key=idempotency_key,
        invoice=invoice,
        metadata={
            'credits': credits,
            **(metadata or {}),
        },
    )


def debit_usage(
    *,
    school,
    channel: str,
    units: int,
    idempotency_key: str,
    guardian_delivery=None,
    metadata: dict | None = None,
) -> CreditLedgerEntry:
    units = max(1, int(units))
    return write_ledger_entry(
        school=school,
        channel=channel,
        entry_type=CreditLedgerEntry.EntryType.USAGE_DEBIT,
        delta=-units,
        idempotency_key=idempotency_key,
        guardian_delivery=guardian_delivery,
        metadata={'units': units, **(metadata or {})},
    )


def reverse_usage(
    *,
    school,
    channel: str,
    units: int,
    source_idempotency_key: str,
    metadata: dict | None = None,
) -> CreditLedgerEntry:
    """Credit back a prior usage debit (e.g. provider send failed after reserve)."""
    units = max(1, int(units))
    return write_ledger_entry(
        school=school,
        channel=channel,
        entry_type=CreditLedgerEntry.EntryType.REVERSAL,
        delta=units,
        idempotency_key=f'reversal:{source_idempotency_key}',
        metadata={
            'reversed_key': source_idempotency_key,
            'units': units,
            **(metadata or {}),
        },
    )


def manual_adjust(
    *,
    school,
    channel: str,
    delta: int,
    idempotency_key: str,
    actor=None,
    metadata: dict | None = None,
) -> CreditLedgerEntry:
    return write_ledger_entry(
        school=school,
        channel=channel,
        entry_type=CreditLedgerEntry.EntryType.MANUAL_ADJUST,
        delta=int(delta),
        idempotency_key=idempotency_key,
        actor_platform_user=actor,
        allow_negative=False if delta < 0 else True,
        metadata=metadata or {},
    )
