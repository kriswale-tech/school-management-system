"""Worker-side guardian SMS/email batch delivery."""

from __future__ import annotations

import logging

from django.conf import settings
from schools.models import School

from communications.services.allowances import classify_items
from communications.services.gates import filter_items_by_credits
from communications.services.ledger import InsufficientCredits, debit_usage
from communications.services.pricing import snapshot_for_channel
from communications.services.refunds import record_unbilled_send
from communications.services.segments import sms_segment_count
from notifications.models import GuardianDelivery
from notifications.services.outbound import (
    filter_new_items,
    filter_processable_sms,
    mark_sms_processing,
    record_delivery_result,
    update_sms_attempt,
)
from notifications.services.resend_batch import send_email_batch
from shared.services.arkesel_sms import send_personalized_sms_batch

logger = logging.getLogger(__name__)


def _school_map(items: list[dict]) -> dict:
    school_ids = {item['school_id'] for item in items}
    return {
        str(school.pk): school
        for school in School.objects.filter(pk__in=school_ids)
    }


def _skip_item(item: dict, *, channel: str, reason: str) -> None:
    friendly = {
        'insufficient_credits': 'Not enough messaging credits to send.',
        'school_missing': 'School could not be found for this message.',
        'school_inaccessible': 'School is not currently able to send messages.',
        'allowance_exhausted': 'Free messaging allowance is exhausted.',
    }.get(reason, reason.replace('_', ' ').capitalize())
    body = item.get('body') or item.get('text_body') or item.get('subject') or ''
    classification = item.get('billing_classification') or GuardianDelivery.BillingClassification.PAID
    if channel == GuardianDelivery.Channel.SMS:
        delivery = update_sms_attempt(
            idempotency_key=item['idempotency_key'],
            status=GuardianDelivery.Status.SKIPPED,
            user_error_message=friendly,
            error_message=friendly,
        )
        if delivery is not None:
            delivery.skip_reason = reason[:200]
            delivery.segments = sms_segment_count(body)
            delivery.billing_classification = classification
            delivery.save(
                update_fields=[
                    'skip_reason',
                    'segments',
                    'billing_classification',
                    'updated_at',
                ],
            )
            return
    record_delivery_result(
        school_id=item['school_id'],
        parent_id=item['parent_id'],
        student_id=item.get('student_id'),
        event_type=item['event_type'],
        channel=channel,
        status=GuardianDelivery.Status.SKIPPED,
        recipient_address=item['recipient_address'],
        body_preview=body,
        body_text=body,
        idempotency_key=item['idempotency_key'],
        skip_reason=reason[:200],
        user_error_message=friendly,
        error_message=friendly,
        source_delivery_id=item.get('source_delivery_id'),
        segments=sms_segment_count(body) if channel == GuardianDelivery.Channel.SMS else 0,
    )


def _apply_snapshots(delivery, *, channel: str, body: str, units: int, item: dict) -> None:
    if delivery is None:
        return
    snapshot = snapshot_for_channel(channel=channel, body=body, units=units)
    delivery.billing_classification = (
        item.get('billing_classification') or GuardianDelivery.BillingClassification.PAID
    )
    allowance_id = item.get('allowance_id')
    if allowance_id:
        delivery.allowance_id = allowance_id
    delivery.provider_cost_snapshot_ghs = snapshot.get('provider_cost_snapshot_ghs')
    delivery.school_unit_price_snapshot_ghs = snapshot.get('school_unit_price_snapshot_ghs')
    delivery.encoding_snapshot = snapshot.get('encoding_snapshot') or ''
    delivery.segment_limit_snapshot = snapshot.get('segment_limit_snapshot') or {}
    delivery.segments = units if channel == GuardianDelivery.Channel.SMS else delivery.segments
    delivery.save(
        update_fields=[
            'billing_classification',
            'allowance_id',
            'provider_cost_snapshot_ghs',
            'school_unit_price_snapshot_ghs',
            'encoding_snapshot',
            'segment_limit_snapshot',
            'segments',
            'updated_at',
        ],
    )


def _debit_after_send(*, school, channel: str, item: dict, delivery) -> int:
    if not item.get('billable', True):
        return 0
    if item.get('billing_classification') in (
        GuardianDelivery.BillingClassification.FREE,
        GuardianDelivery.BillingClassification.SPONSORED,
    ):
        return 0
    units = int(item.get('units') or delivery.segments or 1)
    try:
        debit_usage(
            school=school,
            channel=channel,
            units=units,
            idempotency_key=f'usage:{item["idempotency_key"]}',
            guardian_delivery=delivery,
            metadata={
                'event_type': item.get('event_type'),
                'recipient': item.get('recipient_address'),
                'billing_classification': item.get('billing_classification'),
            },
        )
        return units
    except InsufficientCredits:
        logger.error(
            'Guardian %s sent but credit debit failed for %s (school=%s)',
            channel,
            item.get('idempotency_key'),
            school.pk,
        )
        record_unbilled_send(
            delivery=delivery,
            school=school,
            channel=channel,
            units=units,
        )
        return 0


def _prepare_school_batch(*, school, channel: str, school_items: list[dict]):
    """Classify then gate paid items by credits. Returns sendable + skip counts."""
    paid, covered, skipped = classify_items(
        school=school,
        channel=channel,
        items=school_items,
    )
    sendable: list[dict] = []
    skipped_items: list[dict] = list(skipped)

    if paid:
        ok_items, credit_skipped = filter_items_by_credits(school, channel, paid)
        sendable.extend(ok_items)
        skipped_items.extend(credit_skipped)

    # Free/sponsored never touch the school wallet.
    sendable.extend(covered)
    return sendable, skipped_items


def deliver_guardian_sms_batch(items: list[dict]) -> dict:
    """Send one Celery chunk (≤100) of guardian SMS items."""
    fresh = filter_processable_sms(items)
    if not fresh:
        return {'sent': 0, 'failed': 0, 'skipped': len(items), 'unknown': 0}

    schools = _school_map(fresh)
    sendable: list[dict] = []
    skipped_pre = 0
    by_school: dict[str, list[dict]] = {}
    for item in fresh:
        by_school.setdefault(str(item['school_id']), []).append(item)

    for school_id, school_items in by_school.items():
        school = schools.get(school_id)
        if school is None:
            for item in school_items:
                _skip_item(item, channel=GuardianDelivery.Channel.SMS, reason='school_missing')
                skipped_pre += 1
            continue
        ok_items, skipped_items = _prepare_school_batch(
            school=school,
            channel=GuardianDelivery.Channel.SMS,
            school_items=school_items,
        )
        for item in skipped_items:
            _skip_item(
                item,
                channel=GuardianDelivery.Channel.SMS,
                reason=item.get('skip_reason') or 'insufficient_credits',
            )
            skipped_pre += 1
        sendable.extend(ok_items)

    if not sendable:
        return {
            'sent': 0,
            'failed': 0,
            'unknown': 0,
            'skipped': len(items) - len(fresh) + skipped_pre,
        }

    for item in sendable:
        mark_sms_processing(item['idempotency_key'])

    payload = [
        {
            'phone': item['recipient_address'],
            'message': item['body'],
            'key': item['idempotency_key'],
        }
        for item in sendable
    ]
    results = send_personalized_sms_batch(payload)
    by_key = {row['key']: row for row in results}

    sent = 0
    failed = 0
    unknown = 0
    for item in sendable:
        key = item['idempotency_key']
        result = by_key.get(key) or {}
        school = schools[str(item['school_id'])]
        outcome = result.get('outcome') or ('submitted' if result.get('ok') else 'failed')
        units = int(item.get('units') or sms_segment_count(item.get('body') or ''))

        if outcome == 'submitted' or result.get('ok'):
            delivery = update_sms_attempt(
                idempotency_key=key,
                status=GuardianDelivery.Status.SUBMITTED,
                provider_message_id=result.get('provider_message_id', ''),
                provider_status='SUBMITTED',
                user_error_message='',
                error_message='',
            )
            _apply_snapshots(
                delivery,
                channel=GuardianDelivery.Channel.SMS,
                body=item.get('body') or '',
                units=units,
                item=item,
            )
            charged = 0
            if delivery is not None:
                charged = _debit_after_send(
                    school=school,
                    channel=GuardianDelivery.Channel.SMS,
                    item={**item, 'units': units},
                    delivery=delivery,
                )
                if charged and delivery.credits_charged != charged:
                    delivery.credits_charged = charged
                    delivery.segments = units
                    delivery.save(update_fields=['credits_charged', 'segments', 'updated_at'])
            sent += 1
            if settings.DEBUG:
                print(
                    f'Guardian SMS SUBMITTED for {item["recipient_address"]} | '
                    f'{item["event_type"]} | id={result.get("provider_message_id")} '
                    f'| student={item.get("student_id")}'
                )
        elif outcome == 'unknown':
            user_msg = result.get('user_message') or (
                'SMS submission could not be confirmed.'
            )
            logger.error(
                'Guardian SMS UNKNOWN for key=%s phone=%s technical=%s',
                key,
                item.get('recipient_address'),
                result.get('error'),
            )
            update_sms_attempt(
                idempotency_key=key,
                status=GuardianDelivery.Status.UNKNOWN,
                user_error_message=user_msg,
                error_message=user_msg,
            )
            unknown += 1
        else:
            user_msg = result.get('user_message') or 'The SMS could not be sent.'
            logger.error(
                'Guardian SMS FAILED for key=%s phone=%s technical=%s',
                key,
                item.get('recipient_address'),
                result.get('error'),
            )
            update_sms_attempt(
                idempotency_key=key,
                status=GuardianDelivery.Status.FAILED,
                user_error_message=user_msg,
                error_message=user_msg,
            )
            failed += 1
            if settings.DEBUG:
                print(f'Guardian SMS FAILED for {item["recipient_address"]}: {user_msg}')

    return {
        'sent': sent,
        'failed': failed,
        'unknown': unknown,
        'skipped': len(items) - len(fresh) + skipped_pre,
    }


def deliver_guardian_email_batch(items: list[dict]) -> dict:
    """Send one Celery chunk (≤100) of guardian emails via Resend batch API."""
    fresh = filter_new_items(items)
    if not fresh:
        return {'sent': 0, 'failed': 0, 'skipped': len(items)}

    schools = _school_map(fresh)
    sendable: list[dict] = []
    skipped_pre = 0
    by_school: dict[str, list[dict]] = {}
    for item in fresh:
        by_school.setdefault(str(item['school_id']), []).append(item)

    for school_id, school_items in by_school.items():
        school = schools.get(school_id)
        if school is None:
            for item in school_items:
                _skip_item(item, channel=GuardianDelivery.Channel.EMAIL, reason='school_missing')
                skipped_pre += 1
            continue
        ok_items, skipped_items = _prepare_school_batch(
            school=school,
            channel=GuardianDelivery.Channel.EMAIL,
            school_items=school_items,
        )
        for item in skipped_items:
            _skip_item(
                item,
                channel=GuardianDelivery.Channel.EMAIL,
                reason=item.get('skip_reason') or 'insufficient_credits',
            )
            skipped_pre += 1
        sendable.extend(ok_items)

    if not sendable:
        return {
            'sent': 0,
            'failed': 0,
            'skipped': len(items) - len(fresh) + skipped_pre,
        }

    payload = [
        {
            'key': item['idempotency_key'],
            'to': item['recipient_address'],
            'subject': item['subject'],
            'text': item.get('text_body', ''),
            'html': item.get('html_body', ''),
        }
        for item in sendable
    ]
    results = send_email_batch(payload)
    by_key = {row['key']: row for row in results}

    sent = 0
    failed = 0
    for item in sendable:
        key = item['idempotency_key']
        result = by_key.get(key) or {}
        school = schools[str(item['school_id'])]
        body = item.get('text_body', '')
        if result.get('ok'):
            delivery = record_delivery_result(
                school_id=item['school_id'],
                parent_id=item['parent_id'],
                student_id=item.get('student_id'),
                event_type=item['event_type'],
                channel=GuardianDelivery.Channel.EMAIL,
                status=GuardianDelivery.Status.SUBMITTED,
                recipient_address=item['recipient_address'],
                body_preview=body[:500],
                body_text=body,
                idempotency_key=key,
                provider_message_id=result.get('provider_message_id', ''),
                source_delivery_id=item.get('source_delivery_id'),
            )
            _apply_snapshots(
                delivery,
                channel=GuardianDelivery.Channel.EMAIL,
                body=body,
                units=int(item.get('units') or 1),
                item=item,
            )
            charged = _debit_after_send(
                school=school,
                channel=GuardianDelivery.Channel.EMAIL,
                item=item,
                delivery=delivery,
            )
            if delivery is not None and charged:
                delivery.credits_charged = charged
                delivery.save(update_fields=['credits_charged', 'updated_at'])
            sent += 1
        else:
            user_msg = 'The email could not be sent. Please try again.'
            logger.error(
                'Guardian email FAILED for key=%s technical=%s',
                key,
                result.get('error'),
            )
            record_delivery_result(
                school_id=item['school_id'],
                parent_id=item['parent_id'],
                student_id=item.get('student_id'),
                event_type=item['event_type'],
                channel=GuardianDelivery.Channel.EMAIL,
                status=GuardianDelivery.Status.FAILED,
                recipient_address=item['recipient_address'],
                body_preview=(item.get('subject') or '')[:500],
                body_text=body,
                idempotency_key=key,
                error_message=user_msg,
                user_error_message=user_msg,
                source_delivery_id=item.get('source_delivery_id'),
            )
            failed += 1

    return {
        'sent': sent,
        'failed': failed,
        'skipped': len(items) - len(fresh) + skipped_pre,
    }
