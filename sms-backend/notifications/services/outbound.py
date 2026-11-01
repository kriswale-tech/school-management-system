"""Queue guardian SMS/email for Celery delivery in batches of 100."""

from __future__ import annotations

import logging
from typing import Iterable

from django.db import IntegrityError, transaction

from notifications.models import GuardianDelivery
from shared.services.arkesel_sms import ARKESEL_SMS_BATCH_SIZE

logger = logging.getLogger(__name__)

GUARDIAN_OUTBOUND_BATCH_SIZE = ARKESEL_SMS_BATCH_SIZE  # 100 — SMS and email


def chunked(items: list, size: int = GUARDIAN_OUTBOUND_BATCH_SIZE) -> Iterable[list]:
    for start in range(0, len(items), size):
        yield items[start:start + size]


def _existing_keys(keys: list[str]) -> set[str]:
    if not keys:
        return set()
    return set(
        GuardianDelivery.objects.filter(idempotency_key__in=keys).values_list(
            'idempotency_key',
            flat=True,
        ),
    )


def filter_new_items(items: list[dict]) -> list[dict]:
    """Drop items whose idempotency keys are already recorded."""
    existing = _existing_keys([str(item['idempotency_key']) for item in items])
    return [item for item in items if str(item['idempotency_key']) not in existing]


def enqueue_guardian_sms(items: list[dict]) -> int:
    """Enqueue SMS items (dicts) in Celery batches. Returns number queued."""
    fresh = filter_new_items(items)
    if not fresh:
        return 0
    from notifications.tasks import deliver_guardian_sms_batch_task

    queued = 0
    for batch in chunked(fresh):
        deliver_guardian_sms_batch_task.delay(batch)
        queued += len(batch)
    return queued


def enqueue_guardian_email(items: list[dict]) -> int:
    """Enqueue email items (dicts) in Celery batches. Returns number queued."""
    fresh = filter_new_items(items)
    if not fresh:
        return 0
    from notifications.tasks import deliver_guardian_email_batch_task

    queued = 0
    for batch in chunked(fresh):
        deliver_guardian_email_batch_task.delay(batch)
        queued += len(batch)
    return queued


def enqueue_guardian_outbound(*, sms_items: list[dict], email_items: list[dict]) -> dict:
    """Enqueue both channels after the surrounding transaction commits when needed."""
    sms_count = enqueue_guardian_sms(sms_items)
    email_count = enqueue_guardian_email(email_items)
    return {'sms': sms_count, 'email': email_count}


def schedule_guardian_outbound(*, sms_items: list[dict], email_items: list[dict]) -> None:
    """Enqueue after DB commit so workers never race uncommitted rows."""

    def _run():
        enqueue_guardian_outbound(sms_items=sms_items, email_items=email_items)

    transaction.on_commit(_run)


def record_delivery_result(
    *,
    school_id,
    parent_id,
    student_id,
    event_type: str,
    channel: str,
    status: str,
    recipient_address: str,
    body_preview: str,
    idempotency_key: str,
    provider_message_id: str = '',
    error_message: str = '',
    skip_reason: str = '',
) -> GuardianDelivery | None:
    try:
        # Savepoint so a duplicate key does not break the outer transaction.
        with transaction.atomic():
            return GuardianDelivery.objects.create(
                school_id=school_id,
                parent_id=parent_id,
                student_id=student_id or None,
                event_type=event_type,
                channel=channel,
                status=status,
                recipient_address=recipient_address or '',
                body_preview=(body_preview or '')[:500],
                provider_message_id=(provider_message_id or '')[:100],
                error_message=(error_message or '')[:500],
                skip_reason=(skip_reason or '')[:200],
                idempotency_key=idempotency_key,
            )
    except IntegrityError:
        logger.info('Guardian delivery already recorded for %s', idempotency_key)
        return None
