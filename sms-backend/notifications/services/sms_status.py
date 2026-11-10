"""Map Arkesel DLR / poll statuses onto GuardianDelivery (idempotent)."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from notifications.models import GuardianDelivery

logger = logging.getLogger(__name__)

# Provider statuses documented by Arkesel (query param ``status`` on callback_url).
PROVIDER_TO_INTERNAL = {
    'DELIVERED': GuardianDelivery.Status.DELIVERED,
    'SUBMITTED': GuardianDelivery.Status.SUBMITTED,
    'QUEUED': GuardianDelivery.Status.QUEUED,
    'NOT_DELIVERED': GuardianDelivery.Status.FAILED,
    'PROHIBITED': GuardianDelivery.Status.FAILED,
    'EXPIRED': GuardianDelivery.Status.FAILED,
    'FAILED': GuardianDelivery.Status.FAILED,
    'REJECTED': GuardianDelivery.Status.FAILED,
}

PROVIDER_USER_ERROR = {
    'NOT_DELIVERED': 'The network could not deliver this SMS.',
    'PROHIBITED': 'This SMS was blocked by the network or sender rules.',
    'EXPIRED': 'This SMS expired before it could be delivered.',
    'FAILED': 'The SMS could not be delivered.',
    'REJECTED': 'The SMS was rejected by the provider.',
}

# Rank for monotonic / idempotent updates (never move backwards from a final state).
STATUS_RANK = {
    GuardianDelivery.Status.QUEUED: 10,
    GuardianDelivery.Status.PROCESSING: 20,
    GuardianDelivery.Status.SUBMITTED: 30,
    GuardianDelivery.Status.UNKNOWN: 25,
    GuardianDelivery.Status.DELIVERED: 50,
    GuardianDelivery.Status.FAILED: 50,
    GuardianDelivery.Status.SKIPPED: 50,
    # Legacy alias kept during transition
    GuardianDelivery.Status.SENT: 30,
}

FINAL_STATUSES = frozenset({
    GuardianDelivery.Status.DELIVERED,
    GuardianDelivery.Status.FAILED,
    GuardianDelivery.Status.SKIPPED,
})

NON_RESENDABLE = frozenset({
    GuardianDelivery.Status.QUEUED,
    GuardianDelivery.Status.PROCESSING,
    GuardianDelivery.Status.SUBMITTED,
    GuardianDelivery.Status.DELIVERED,
    GuardianDelivery.Status.SENT,
})


def normalize_provider_status(raw: str | None) -> str:
    return (raw or '').strip().upper()


def map_provider_status(raw: str | None) -> str | None:
    key = normalize_provider_status(raw)
    if not key:
        return None
    return PROVIDER_TO_INTERNAL.get(key)


def user_error_for_provider(raw: str | None) -> str:
    key = normalize_provider_status(raw)
    return PROVIDER_USER_ERROR.get(key, 'The SMS could not be delivered.')


def _can_transition(current: str, new: str) -> bool:
    if current == new:
        return True
    if current in FINAL_STATUSES:
        return False
    return STATUS_RANK.get(new, 0) >= STATUS_RANK.get(current, 0)


@transaction.atomic
def apply_provider_status(
    *,
    sms_id: str,
    provider_status: str,
    source: str = 'webhook',
) -> GuardianDelivery | None:
    """Apply an Arkesel status to the matching SMS delivery (school-scoped by sms_id).

    Idempotent: duplicate callbacks with the same or weaker status are no-ops.
    Unknown ``sms_id`` values are ignored (open webhook).
    """
    sms_id = (sms_id or '').strip()
    if not sms_id:
        return None

    delivery = (
        GuardianDelivery.objects.select_for_update()
        .filter(
            channel=GuardianDelivery.Channel.SMS,
            provider_message_id=sms_id,
        )
        .first()
    )
    if delivery is None:
        logger.info('Ignoring Arkesel %s for unknown sms_id=%s', source, sms_id)
        return None

    mapped = map_provider_status(provider_status)
    normalized = normalize_provider_status(provider_status)
    if mapped is None:
        logger.warning(
            'Unrecognized Arkesel status %r for delivery=%s sms_id=%s via %s',
            provider_status,
            delivery.pk,
            sms_id,
            source,
        )
        # Keep provider raw for ops; do not invent a status.
        if delivery.provider_status != normalized:
            delivery.provider_status = normalized[:40]
            delivery.status_updated_at = timezone.now()
            delivery.save(update_fields=['provider_status', 'status_updated_at', 'updated_at'])
        return delivery

    if not _can_transition(delivery.status, mapped):
        logger.info(
            'Skip Arkesel %s %s→%s for delivery=%s (current=%s)',
            source,
            normalized,
            mapped,
            delivery.pk,
            delivery.status,
        )
        return delivery

    updates = {
        'provider_status': normalized[:40],
        'status_updated_at': timezone.now(),
    }
    if delivery.status != mapped:
        updates['status'] = mapped

    if mapped == GuardianDelivery.Status.FAILED:
        friendly = user_error_for_provider(normalized)
        updates['error_message'] = friendly[:500]
        updates['user_error_message'] = friendly[:240]
    elif mapped == GuardianDelivery.Status.DELIVERED:
        updates['error_message'] = ''
        updates['user_error_message'] = ''

    for field, value in updates.items():
        setattr(delivery, field, value)
    delivery.save(update_fields=[*updates.keys(), 'updated_at'])
    logger.info(
        'Delivery %s updated via %s to %s (provider=%s)',
        delivery.pk,
        source,
        delivery.status,
        normalized,
    )
    if mapped == GuardianDelivery.Status.FAILED:
        try:
            from communications.services.refunds import refund_failed_delivery

            refund_failed_delivery(delivery, source=source)
        except Exception:
            logger.exception(
                'Failed to auto-refund delivery=%s after provider failure',
                delivery.pk,
            )
    return delivery


def pending_sms_for_poll(*, older_than_seconds: int = 120, limit: int = 100):
    """SMS rows still awaiting a final DLR, with a provider id to look up."""
    cutoff = timezone.now() - timedelta(seconds=older_than_seconds)
    return (
        GuardianDelivery.objects.filter(
            channel=GuardianDelivery.Channel.SMS,
            status__in=[
                GuardianDelivery.Status.SUBMITTED,
                GuardianDelivery.Status.QUEUED,
                GuardianDelivery.Status.PROCESSING,
                GuardianDelivery.Status.UNKNOWN,
                GuardianDelivery.Status.SENT,
            ],
        )
        .exclude(provider_message_id='')
        .filter(status_updated_at__lte=cutoff)
        .order_by('status_updated_at')[:limit]
    )
