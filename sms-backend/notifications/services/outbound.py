"""Queue guardian SMS/email for Celery delivery in batches of 100."""

from __future__ import annotations

import logging
from typing import Iterable
from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone

from communications.services.segments import sms_segment_count
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
    """Drop items whose idempotency keys are already recorded (email path)."""
    existing = _existing_keys([str(item['idempotency_key']) for item in items])
    return [item for item in items if str(item['idempotency_key']) not in existing]


def ensure_queued_sms(item: dict) -> GuardianDelivery | None:
    """Create a Queued SMS delivery row, or return the existing one for this key."""
    key = str(item['idempotency_key'])
    body = item.get('body') or ''
    segments = sms_segment_count(body)
    source_id = item.get('source_delivery_id') or None
    try:
        with transaction.atomic():
            return GuardianDelivery.objects.create(
                school_id=item['school_id'],
                parent_id=item['parent_id'],
                student_id=item.get('student_id') or None,
                event_type=item['event_type'],
                channel=GuardianDelivery.Channel.SMS,
                status=GuardianDelivery.Status.QUEUED,
                recipient_address=item.get('recipient_address') or '',
                body_preview=(body or '')[:500],
                body_text=body or '',
                idempotency_key=key,
                source_delivery_id=source_id,
                segments=segments,
                status_updated_at=timezone.now(),
            )
    except IntegrityError:
        return GuardianDelivery.objects.filter(idempotency_key=key).first()


def filter_processable_sms(items: list[dict]) -> list[dict]:
    """Keep SMS items that are new or still in queued/processing (Celery-safe)."""
    keys = [str(item['idempotency_key']) for item in items]
    existing = {
        row.idempotency_key: row
        for row in GuardianDelivery.objects.filter(idempotency_key__in=keys)
    }
    processable: list[dict] = []
    for item in items:
        key = str(item['idempotency_key'])
        row = existing.get(key)
        if row is None:
            row = ensure_queued_sms(item)
            if row is None:
                continue
            existing[key] = row
        if row.status in (
            GuardianDelivery.Status.QUEUED,
            GuardianDelivery.Status.PROCESSING,
        ):
            processable.append(item)
        elif row.status == GuardianDelivery.Status.SUBMITTED and not row.credits_charged:
            # Finish debit if prior attempt crashed after submit.
            processable.append(item)
    return processable


def enqueue_guardian_sms(items: list[dict]) -> int:
    """Enqueue SMS items (dicts) in Celery batches. Returns number queued."""
    ready: list[dict] = []
    for item in items:
        row = ensure_queued_sms(item)
        if row is None:
            continue
        if row.status in (
            GuardianDelivery.Status.QUEUED,
            GuardianDelivery.Status.PROCESSING,
        ):
            ready.append(item)
    if not ready:
        return 0
    from notifications.tasks import deliver_guardian_sms_batch_task

    queued = 0
    for batch in chunked(ready):
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


def mark_sms_processing(idempotency_key: str) -> GuardianDelivery | None:
    delivery = GuardianDelivery.objects.filter(idempotency_key=idempotency_key).first()
    if delivery is None:
        return None
    if delivery.status not in (
        GuardianDelivery.Status.QUEUED,
        GuardianDelivery.Status.PROCESSING,
    ):
        return delivery
    delivery.status = GuardianDelivery.Status.PROCESSING
    delivery.status_updated_at = timezone.now()
    delivery.save(update_fields=['status', 'status_updated_at', 'updated_at'])
    return delivery


def update_sms_attempt(
    *,
    idempotency_key: str,
    status: str,
    provider_message_id: str = '',
    user_error_message: str = '',
    error_message: str = '',
    credits_charged: int | None = None,
    provider_status: str = '',
) -> GuardianDelivery | None:
    delivery = GuardianDelivery.objects.filter(idempotency_key=idempotency_key).first()
    if delivery is None:
        return None
    delivery.status = status
    delivery.status_updated_at = timezone.now()
    if provider_message_id:
        delivery.provider_message_id = provider_message_id[:100]
    if provider_status:
        delivery.provider_status = provider_status[:40]
    if user_error_message is not None:
        delivery.user_error_message = (user_error_message or '')[:240]
        delivery.error_message = (error_message or user_error_message or '')[:500]
    if credits_charged is not None:
        delivery.credits_charged = credits_charged
    delivery.save(
        update_fields=[
            'status',
            'status_updated_at',
            'provider_message_id',
            'provider_status',
            'user_error_message',
            'error_message',
            'credits_charged',
            'updated_at',
        ],
    )
    return delivery


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
    body_text: str = '',
    segments: int = 0,
    user_error_message: str = '',
    source_delivery_id: UUID | str | None = None,
    credits_charged: int = 0,
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
                body_text=body_text or body_preview or '',
                provider_message_id=(provider_message_id or '')[:100],
                error_message=(error_message or '')[:500],
                user_error_message=(user_error_message or error_message or '')[:240],
                skip_reason=(skip_reason or '')[:200],
                idempotency_key=idempotency_key,
                source_delivery_id=source_delivery_id or None,
                segments=segments or 0,
                credits_charged=credits_charged or 0,
                status_updated_at=timezone.now(),
            )
    except IntegrityError:
        logger.info('Guardian delivery already recorded for %s', idempotency_key)
        existing = GuardianDelivery.objects.filter(idempotency_key=idempotency_key).first()
        if existing and channel == GuardianDelivery.Channel.SMS:
            return update_sms_attempt(
                idempotency_key=idempotency_key,
                status=status,
                provider_message_id=provider_message_id,
                user_error_message=user_error_message or error_message,
                error_message=error_message,
                credits_charged=credits_charged or None,
            )
        return existing
