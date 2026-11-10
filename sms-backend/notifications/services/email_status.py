"""Apply SES / legacy Resend webhook events to email delivery rows (v4.1 §2.8).

Advances status idempotently and triggers the refund policy on a post-acceptance
failure — never a second debit and never a second refund.
"""

from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from notifications.models import (
    GuardianDelivery,
    PlatformOutboundDelivery,
    ResendWebhookEvent,
)

logger = logging.getLogger(__name__)

# Resend event types → internal GuardianDelivery status.
EVENT_TO_STATUS = {
    'email.sent': GuardianDelivery.Status.SUBMITTED,
    'email.delivered': GuardianDelivery.Status.DELIVERED,
    'email.bounced': GuardianDelivery.Status.FAILED,
    'email.failed': GuardianDelivery.Status.FAILED,
    'email.delivery_delayed': GuardianDelivery.Status.SUBMITTED,
    # A complaint does not change deliverability; it is recorded on provider_status.
    'email.complained': None,
    'email.opened': None,
    'email.clicked': None,
}

# Amazon SES eventType / notificationType → same internal statuses.
SES_EVENT_TO_STATUS = {
    'send': GuardianDelivery.Status.SUBMITTED,
    'delivery': GuardianDelivery.Status.DELIVERED,
    'bounce': GuardianDelivery.Status.FAILED,
    'reject': GuardianDelivery.Status.FAILED,
    'complaint': None,
    'deliverydelay': GuardianDelivery.Status.SUBMITTED,
    'open': None,
    'click': None,
    # Local / placeholder test events.
    'ses.send': GuardianDelivery.Status.SUBMITTED,
    'ses.delivery': GuardianDelivery.Status.DELIVERED,
    'ses.bounce': GuardianDelivery.Status.FAILED,
    'ses.reject': GuardianDelivery.Status.FAILED,
}

EVENT_USER_ERROR = {
    'email.bounced': 'The email address rejected this message.',
    'email.failed': 'The email could not be sent.',
    'bounce': 'The email address rejected this message.',
    'reject': 'The email could not be sent.',
    'ses.bounce': 'The email address rejected this message.',
    'ses.reject': 'The email could not be sent.',
}

STATUS_RANK = {
    GuardianDelivery.Status.QUEUED: 10,
    GuardianDelivery.Status.PROCESSING: 20,
    GuardianDelivery.Status.UNKNOWN: 25,
    GuardianDelivery.Status.SUBMITTED: 30,
    GuardianDelivery.Status.SENT: 30,
    GuardianDelivery.Status.DELIVERED: 50,
    GuardianDelivery.Status.FAILED: 50,
    GuardianDelivery.Status.SKIPPED: 50,
}

FINAL_STATUSES = frozenset({
    GuardianDelivery.Status.DELIVERED,
    GuardianDelivery.Status.FAILED,
    GuardianDelivery.Status.SKIPPED,
})


def extract_event_type(payload: dict) -> str:
    if not isinstance(payload, dict):
        return ''
    return str(payload.get('type') or payload.get('event') or '').strip().lower()


def extract_email_id(payload: dict) -> str:
    """Pull the Resend email id out of a webhook payload."""
    if not isinstance(payload, dict):
        return ''
    data = payload.get('data')
    if isinstance(data, dict):
        for key in ('email_id', 'id', 'message_id'):
            value = data.get(key)
            if value:
                return str(value)
    for key in ('email_id', 'id'):
        value = payload.get(key)
        if value:
            return str(value)
    return ''


def extract_ses_event_type(payload: dict) -> str:
    """Normalize SES eventType / notificationType (and local stubs)."""
    if not isinstance(payload, dict):
        return ''
    raw = (
        payload.get('eventType')
        or payload.get('notificationType')
        or payload.get('type')
        or payload.get('event')
        or ''
    )
    return str(raw).strip().lower()


def extract_ses_message_id(payload: dict) -> str:
    """Pull the SES message id from an event or SNS-unwrapped payload."""
    if not isinstance(payload, dict):
        return ''
    mail = payload.get('mail')
    if isinstance(mail, dict) and mail.get('messageId'):
        return str(mail['messageId'])
    for key in ('mail', 'bounce', 'delivery', 'complaint', 'reject'):
        block = payload.get(key)
        if isinstance(block, dict) and block.get('messageId'):
            return str(block['messageId'])
    for key in ('messageId', 'message_id', 'provider_message_id', 'id'):
        value = payload.get(key)
        if value and key != 'id':
            return str(value)
        if key == 'id' and value and str(value).startswith(('ses-', 'console-')):
            return str(value)
    return ''


def _can_transition(current: str, new: str) -> bool:
    if current == new:
        return True
    if current in FINAL_STATUSES:
        return False
    return STATUS_RANK.get(new, 0) >= STATUS_RANK.get(current, 0)


def _apply_email_event(
    *,
    event_type: str,
    payload: dict,
    provider_id: str,
    status_map: dict,
    refund_source_prefix: str,
) -> dict:
    """Shared apply path for SES and legacy Resend events."""
    outcome = {'matched_type': '', 'matched_id': '', 'status': None, 'refunded': False}
    provider_id = (provider_id or '').strip()
    if not provider_id:
        return outcome

    normalized = (event_type or '').strip().lower()
    if normalized not in status_map:
        logger.info('Ignoring unknown email event type %r', event_type)

    mapped = status_map.get(normalized)
    provider_status = normalized.replace('email.', '').replace('ses.', '').upper()[:40]

    delivery = (
        GuardianDelivery.objects.select_for_update()
        .filter(channel=GuardianDelivery.Channel.EMAIL, provider_message_id=provider_id)
        .first()
    )
    if delivery is not None:
        outcome['matched_type'] = 'guardian_delivery'
        outcome['matched_id'] = str(delivery.pk)
        outcome['status'] = _update_guardian(
            delivery=delivery,
            mapped=mapped,
            provider_status=provider_status,
            event_type=normalized,
        )
        if (
            mapped == GuardianDelivery.Status.FAILED
            and delivery.status == GuardianDelivery.Status.FAILED
        ):
            from communications.services.refunds import refund_failed_delivery

            entry = refund_failed_delivery(
                delivery,
                source=f'{refund_source_prefix}:{normalized}',
            )
            outcome['refunded'] = entry is not None
        return outcome

    platform_row = (
        PlatformOutboundDelivery.objects.select_for_update()
        .filter(
            channel=PlatformOutboundDelivery.Channel.EMAIL,
            provider_message_id=provider_id,
        )
        .first()
    )
    if platform_row is not None:
        outcome['matched_type'] = 'platform_outbound_delivery'
        outcome['matched_id'] = str(platform_row.pk)
        outcome['status'] = _update_platform(
            delivery=platform_row,
            mapped=mapped,
            provider_status=provider_status,
        )
    return outcome


@transaction.atomic
def apply_ses_event(*, event_type: str, payload: dict, message_id: str = '') -> dict:
    """Apply one SES (or local stub) event. Idempotent."""
    provider_id = (message_id or extract_ses_message_id(payload) or '').strip()
    return _apply_email_event(
        event_type=event_type,
        payload=payload,
        provider_id=provider_id,
        status_map=SES_EVENT_TO_STATUS,
        refund_source_prefix='ses',
    )


@transaction.atomic
def apply_resend_event(*, event_type: str, payload: dict, email_id: str = '') -> dict:
    """Apply one legacy Resend event. Idempotent; safe for duplicate deliveries."""
    provider_id = (email_id or extract_email_id(payload) or '').strip()
    return _apply_email_event(
        event_type=event_type,
        payload=payload,
        provider_id=provider_id,
        status_map=EVENT_TO_STATUS,
        refund_source_prefix='resend',
    )


def _update_guardian(*, delivery, mapped, provider_status: str, event_type: str):
    updates = {
        'provider_status': provider_status,
        'status_updated_at': timezone.now(),
    }
    if mapped is not None and _can_transition(delivery.status, mapped):
        if delivery.status != mapped:
            updates['status'] = mapped
        if mapped == GuardianDelivery.Status.FAILED:
            friendly = EVENT_USER_ERROR.get(event_type, 'The email could not be delivered.')
            updates['error_message'] = friendly[:500]
            updates['user_error_message'] = friendly[:240]
        elif mapped == GuardianDelivery.Status.DELIVERED:
            updates['error_message'] = ''
            updates['user_error_message'] = ''

    for field, value in updates.items():
        setattr(delivery, field, value)
    delivery.save(update_fields=[*updates.keys(), 'updated_at'])
    return delivery.status


def _update_platform(*, delivery, mapped, provider_status: str):
    status_map = {
        GuardianDelivery.Status.DELIVERED: PlatformOutboundDelivery.Status.DELIVERED,
        GuardianDelivery.Status.FAILED: PlatformOutboundDelivery.Status.FAILED,
        GuardianDelivery.Status.SUBMITTED: PlatformOutboundDelivery.Status.SUBMITTED,
    }
    target = status_map.get(mapped)
    updates = {'provider_status': provider_status, 'status_updated_at': timezone.now()}
    if target is not None and delivery.status not in (
        PlatformOutboundDelivery.Status.DELIVERED,
        PlatformOutboundDelivery.Status.FAILED,
    ):
        updates['status'] = target
    for field, value in updates.items():
        setattr(delivery, field, value)
    delivery.save(update_fields=[*updates.keys(), 'updated_at'])
    return delivery.status


def record_webhook_event(
    *,
    event_id: str,
    event_type: str,
    payload: dict,
    signature_valid: bool,
) -> tuple[ResendWebhookEvent, bool]:
    """Store the event for idempotency. Returns ``(row, created)``."""
    row, created = ResendWebhookEvent.objects.get_or_create(
        event_id=event_id,
        defaults={
            'event_type': event_type,
            'provider_message_id': extract_email_id(payload)[:100],
            'payload': payload if isinstance(payload, dict) else {},
            'signature_valid': signature_valid,
            'received_at': timezone.now(),
        },
    )
    return row, created
