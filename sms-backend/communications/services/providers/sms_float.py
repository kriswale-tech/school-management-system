"""Platform Arkesel SMS float.

School credit purchases do not load Arkesel. This float is the prepaid wallet
the API key actually spends. It is set from a balance sync (or a manual
capture) and reduced as SMS is accepted, so several schools cannot all send
against one stale reading.

School SMS is held when the float is missing, older than
``ARKESEL_FLOAT_MAX_AGE_MINUTES``, or too small for the next message. Held
messages are not sent and school credits are not debited. Login OTP is never
held; a successful OTP only reduces the float.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from communications.models import Provider, ProviderAccount, ProviderChannel
from communications.services.providers.accounts import get_provider_account
from communications.services.segments import sms_segment_count

logger = logging.getLogger(__name__)

HOLD_UNKNOWN = 'unknown'
HOLD_STALE = 'stale'
HOLD_SHORT = 'short'


@dataclass(frozen=True)
class SmsFloatSplit:
    sendable: list[dict]
    held: list[dict]
    reason: str
    available: int
    tracked: bool


def _arkesel_account() -> ProviderAccount:
    return get_provider_account(provider=Provider.ARKESEL, channel=ProviderChannel.SMS)


def _assumed_units() -> int | None:
    value = getattr(settings, 'ARKESEL_FLOAT_ASSUME_UNITS', None)
    if value is None:
        return None
    return int(value)


def _max_age() -> timedelta:
    minutes = int(getattr(settings, 'ARKESEL_FLOAT_MAX_AGE_MINUTES', 90))
    return timedelta(minutes=max(1, minutes))


def _cooldown() -> timedelta:
    hours = int(getattr(settings, 'ARKESEL_ALERT_COOLDOWN_HOURS', 24))
    return timedelta(hours=max(1, hours))


def _lookback_days() -> int:
    return max(1, int(getattr(settings, 'ARKESEL_USAGE_LOOKBACK_DAYS', 7)))


def _cover_days() -> int:
    return max(1, int(getattr(settings, 'ARKESEL_LOW_BALANCE_DAYS', 3)))


def recent_sms_units() -> int:
    """SMS units accepted by providers over the lookback window."""
    from notifications.models import GuardianDelivery, PlatformOutboundDelivery

    since = timezone.now() - timedelta(days=_lookback_days())
    guardian = (
        GuardianDelivery.objects.filter(
            channel=GuardianDelivery.Channel.SMS,
            status__in=(
                GuardianDelivery.Status.SUBMITTED,
                GuardianDelivery.Status.DELIVERED,
                GuardianDelivery.Status.SENT,
            ),
            created_at__gte=since,
        ).aggregate(total=Sum('segments'))['total']
        or 0
    )
    platform = (
        PlatformOutboundDelivery.objects.filter(
            channel=PlatformOutboundDelivery.Channel.SMS,
            status__in=(
                PlatformOutboundDelivery.Status.SUBMITTED,
                PlatformOutboundDelivery.Status.DELIVERED,
            ),
            created_at__gte=since,
        ).aggregate(total=Sum('units'))['total']
        or 0
    )
    return int(guardian) + int(platform)


def low_balance_threshold() -> int:
    """Units that cover ``ARKESEL_LOW_BALANCE_DAYS`` of recent sending."""
    total = recent_sms_units()
    if total <= 0:
        return 0
    lookback = _lookback_days()
    cover = _cover_days()
    return (total * cover + lookback - 1) // lookback


def _claim(locked: ProviderAccount, field: str, *, now) -> bool:
    previous = getattr(locked, field)
    if previous is not None and now - previous < _cooldown():
        return False
    setattr(locked, field, now)
    return True


def _prepare(items: list[dict]) -> list[dict]:
    prepared = []
    for item in items:
        raw = item.get('units')
        units = int(raw) if raw else sms_segment_count(item.get('body') or '')
        prepared.append({**item, 'units': max(1, units)})
    return prepared


def reserve_school_sms(items: list[dict]) -> SmsFloatSplit:
    """Split a school batch into messages the float can cover, and hold the rest.

    Covered messages decrement the float under a row lock. The caller restores
    units Arkesel rejects via ``settle_school_sms``.
    """
    prepared = _prepare(items)
    if not prepared:
        return SmsFloatSplit([], [], '', 0, False)

    with transaction.atomic():
        locked = (
            ProviderAccount.objects.select_for_update()
            .get(pk=_arkesel_account().pk)
        )
        assumed = _assumed_units()
        if locked.sms_float_units is None or locked.sms_float_synced_at is None:
            if assumed is not None:
                return SmsFloatSplit(prepared, [], '', assumed, False)
            return SmsFloatSplit([], prepared, HOLD_UNKNOWN, 0, False)

        age = timezone.now() - locked.sms_float_synced_at
        available = int(locked.sms_float_units)
        if age > _max_age():
            return SmsFloatSplit([], prepared, HOLD_STALE, max(0, available), False)

        sendable: list[dict] = []
        held: list[dict] = []
        reserved_now = 0
        for item in prepared:
            units = int(item['units'])
            if available >= units:
                sendable.append(item)
                available -= units
                reserved_now += units
            else:
                held.append(item)
        if reserved_now:
            locked.sms_float_units = int(locked.sms_float_units) - reserved_now
            locked.sms_float_reserved = int(locked.sms_float_reserved or 0) + reserved_now
            locked.save(update_fields=['sms_float_units', 'sms_float_reserved', 'updated_at'])
        reason = HOLD_SHORT if held else ''
        return SmsFloatSplit(sendable, held, reason, max(0, available), True)


def settle_school_sms(*, submitted: int, failed: int, unknown: int) -> None:
    """Release the in-flight reservation. Restore units only when Arkesel rejected them.

    Unknown submissions stay consumed until the next balance sync. A failed
    submission is safe to promise again.
    """
    submitted = max(0, int(submitted))
    failed = max(0, int(failed))
    unknown = max(0, int(unknown))
    finished = submitted + failed + unknown
    if finished <= 0:
        return
    with transaction.atomic():
        locked = ProviderAccount.objects.select_for_update().get(pk=_arkesel_account().pk)
        locked.sms_float_reserved = max(0, int(locked.sms_float_reserved or 0) - finished)
        fields = ['sms_float_reserved', 'updated_at']
        if failed and locked.sms_float_units is not None:
            locked.sms_float_units = int(locked.sms_float_units) + failed
            fields.append('sms_float_units')
        locked.save(update_fields=fields)


def consume_unreserved_sms_units(units: int) -> None:
    """Reduce the float for platform SMS that must not be held (login OTP)."""
    units = int(units or 0)
    if units <= 0:
        return
    try:
        with transaction.atomic():
            locked = ProviderAccount.objects.select_for_update().get(pk=_arkesel_account().pk)
            if locked.sms_float_units is None:
                return
            locked.sms_float_units = int(locked.sms_float_units) - units
            locked.save(update_fields=['sms_float_units', 'updated_at'])
    except Exception:
        logger.exception('Could not reduce Arkesel float by %s units', units)


def apply_synced_balance(account: ProviderAccount, sms_balance: int) -> None:
    """Replace the float from an Arkesel reading and email if cover is thin or gone."""
    balance = int(sms_balance)
    now = timezone.now()
    threshold = low_balance_threshold()
    send_empty = False
    send_low = False
    with transaction.atomic():
        locked = ProviderAccount.objects.select_for_update().get(pk=account.pk)
        reserved = int(locked.sms_float_reserved or 0)
        locked.sms_float_units = balance - reserved
        locked.sms_float_synced_at = now
        fields = ['sms_float_units', 'sms_float_synced_at', 'updated_at']
        healthy = balance > 0 and (threshold <= 0 or balance >= threshold)
        if healthy:
            locked.sms_low_balance_alerted_at = None
            locked.sms_hold_alerted_at = None
            fields.extend(['sms_low_balance_alerted_at', 'sms_hold_alerted_at'])
            locked.save(update_fields=fields)
        else:
            if balance <= 0 and _claim(locked, 'sms_hold_alerted_at', now=now):
                send_empty = True
                fields.append('sms_hold_alerted_at')
            elif balance > 0 and _claim(locked, 'sms_low_balance_alerted_at', now=now):
                send_low = True
                fields.append('sms_low_balance_alerted_at')
            locked.save(update_fields=fields)

    if send_empty:
        _email_empty_wallet(balance)
    elif send_low:
        _email_low_wallet(balance, threshold)


def notify_sends_held(*, held: int, reason: str, available: int) -> None:
    """Email platform admins once per cooldown when school SMS is held."""
    held = int(held or 0)
    if held < 1:
        return
    now = timezone.now()
    with transaction.atomic():
        locked = ProviderAccount.objects.select_for_update().get(pk=_arkesel_account().pk)
        if not _claim(locked, 'sms_hold_alerted_at', now=now):
            return
        locked.save(update_fields=['sms_hold_alerted_at', 'updated_at'])
    _email_sends_held(held=held, reason=reason, available=available)


def notify_sync_problem(error: str) -> None:
    """Email when a balance sync fails. School SMS is held once the last reading expires."""
    now = timezone.now()
    with transaction.atomic():
        locked = ProviderAccount.objects.select_for_update().get(pk=_arkesel_account().pk)
        if not _claim(locked, 'sms_hold_alerted_at', now=now):
            return
        locked.save(update_fields=['sms_hold_alerted_at', 'updated_at'])
    from communications.services.platform_mail import send_platform_email

    minutes = int(getattr(settings, 'ARKESEL_FLOAT_MAX_AGE_MINUTES', 90))
    send_platform_email(
        subject='Arkesel balance could not be read',
        body=(
            'The Arkesel balance sync failed, so the platform SMS float was not refreshed.\n\n'
            f'Detail: {(error or "unknown error")[:500]}\n\n'
            f'School SMS keeps sending only while the last good reading is under '
            f'{minutes} minutes old. After that, school SMS is held and school '
            'credits are not debited.\n\n'
            'Check the Arkesel API key and top up the wallet if it is empty. '
            'This notice goes to platform admins who can open Messages.'
        ),
    )


def _email_empty_wallet(balance: int) -> None:
    from communications.services.platform_mail import send_platform_email

    send_platform_email(
        subject='Arkesel SMS wallet is empty',
        body=(
            f'Arkesel reports {balance} SMS units.\n\n'
            'School SMS will be held until you top up. Schools keep the credits '
            'they already bought — those credits are only used after Arkesel accepts '
            'a message.\n\n'
            'This notice goes to platform admins who can open Messages. '
            'It will not repeat until the wallet is topped up, or '
            f'{int(getattr(settings, "ARKESEL_ALERT_COOLDOWN_HOURS", 24))} hours have passed.'
        ),
    )


def _email_low_wallet(balance: int, threshold: int) -> None:
    from communications.services.platform_mail import send_platform_email

    send_platform_email(
        subject='Arkesel SMS balance is low',
        body=(
            f'Arkesel has {balance} SMS units left.\n'
            f'Recent sending needs about {threshold} units to cover the next '
            f'{_cover_days()} days.\n\n'
            'Top up the Arkesel wallet before school messages start being held. '
            'School credit purchases are separate and do not load this wallet.\n\n'
            'This notice goes to platform admins who can open Messages.'
        ),
    )


def _email_sends_held(*, held: int, reason: str, available: int) -> None:
    from communications.services.platform_mail import send_platform_email

    if reason == HOLD_UNKNOWN:
        why = 'No Arkesel balance has been recorded yet.'
    elif reason == HOLD_STALE:
        minutes = int(getattr(settings, 'ARKESEL_FLOAT_MAX_AGE_MINUTES', 90))
        why = f'The last Arkesel balance reading is older than {minutes} minutes.'
    else:
        why = (
            f'The wallet can cover {max(0, int(available))} more units, '
            'which is not enough for every message in the batch.'
        )
    noun = 'message' if held == 1 else 'messages'
    send_platform_email(
        subject='School SMS is paused — Arkesel wallet cannot cover it',
        body=(
            f'{held} school SMS {noun} were held just now and were not sent.\n'
            f'{why}\n\n'
            'School credits were not debited. Top up Arkesel, then the schools can '
            'resend the skipped messages.\n\n'
            'This notice goes to platform admins who can open Messages. '
            'Further holds will not email again until the wallet is healthy, or '
            f'{int(getattr(settings, "ARKESEL_ALERT_COOLDOWN_HOURS", 24))} hours have passed.'
        ),
    )
