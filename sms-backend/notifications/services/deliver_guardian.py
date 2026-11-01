"""Worker-side guardian SMS/email batch delivery."""

from __future__ import annotations

import logging

from django.conf import settings

from notifications.models import GuardianDelivery
from notifications.services.outbound import filter_new_items, record_delivery_result
from notifications.services.resend_batch import send_email_batch
from shared.services.arkesel_sms import send_personalized_sms_batch

logger = logging.getLogger(__name__)


def deliver_guardian_sms_batch(items: list[dict]) -> dict:
    """Send one Celery chunk (≤100) of guardian SMS items."""
    fresh = filter_new_items(items)
    if not fresh:
        return {'sent': 0, 'failed': 0, 'skipped': len(items)}

    payload = [
        {
            'phone': item['recipient_address'],
            'message': item['body'],
            'key': item['idempotency_key'],
        }
        for item in fresh
    ]
    results = send_personalized_sms_batch(payload)
    by_key = {row['key']: row for row in results}

    sent = 0
    failed = 0
    for item in fresh:
        key = item['idempotency_key']
        result = by_key.get(key) or {}
        if result.get('ok'):
            record_delivery_result(
                school_id=item['school_id'],
                parent_id=item['parent_id'],
                student_id=item.get('student_id'),
                event_type=item['event_type'],
                channel=GuardianDelivery.Channel.SMS,
                status=GuardianDelivery.Status.SENT,
                recipient_address=item['recipient_address'],
                body_preview=item.get('body', ''),
                idempotency_key=key,
                provider_message_id=result.get('provider_message_id', ''),
            )
            sent += 1
            if settings.DEBUG:
                print(
                    f'Guardian SMS OK for {item["recipient_address"]} | '
                    f'{item["event_type"]} | id={result.get("provider_message_id")} '
                    f'| student={item.get("student_id")}'
                )
        else:
            error = result.get('error') or 'SMS send failed'
            record_delivery_result(
                school_id=item['school_id'],
                parent_id=item['parent_id'],
                student_id=item.get('student_id'),
                event_type=item['event_type'],
                channel=GuardianDelivery.Channel.SMS,
                status=GuardianDelivery.Status.FAILED,
                recipient_address=item['recipient_address'],
                body_preview=item.get('body', ''),
                idempotency_key=key,
                error_message=error,
            )
            failed += 1
            if settings.DEBUG:
                print(f'Guardian SMS FAILED for {item["recipient_address"]}: {error}')

    return {
        'sent': sent,
        'failed': failed,
        'skipped': len(items) - len(fresh),
    }


def deliver_guardian_email_batch(items: list[dict]) -> dict:
    """Send one Celery chunk (≤100) of guardian emails via Resend batch API."""
    fresh = filter_new_items(items)
    if not fresh:
        return {'sent': 0, 'failed': 0, 'skipped': len(items)}

    payload = [
        {
            'key': item['idempotency_key'],
            'to': item['recipient_address'],
            'subject': item['subject'],
            'text': item.get('text_body', ''),
            'html': item.get('html_body', ''),
        }
        for item in fresh
    ]
    results = send_email_batch(payload)
    by_key = {row['key']: row for row in results}

    sent = 0
    failed = 0
    for item in fresh:
        key = item['idempotency_key']
        result = by_key.get(key) or {}
        if result.get('ok'):
            record_delivery_result(
                school_id=item['school_id'],
                parent_id=item['parent_id'],
                student_id=item.get('student_id'),
                event_type=item['event_type'],
                channel=GuardianDelivery.Channel.EMAIL,
                status=GuardianDelivery.Status.SENT,
                recipient_address=item['recipient_address'],
                body_preview=item.get('text_body', '')[:500],
                idempotency_key=key,
                provider_message_id=result.get('provider_message_id', ''),
            )
            sent += 1
        else:
            record_delivery_result(
                school_id=item['school_id'],
                parent_id=item['parent_id'],
                student_id=item.get('student_id'),
                event_type=item['event_type'],
                channel=GuardianDelivery.Channel.EMAIL,
                status=GuardianDelivery.Status.FAILED,
                recipient_address=item['recipient_address'],
                body_preview=item.get('subject', '')[:500],
                idempotency_key=key,
                error_message=result.get('error') or 'Email send failed',
            )
            failed += 1

    return {
        'sent': sent,
        'failed': failed,
        'skipped': len(items) - len(fresh),
    }
