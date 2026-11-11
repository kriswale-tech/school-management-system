from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from uuid import uuid4

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Trim
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from communications.models import CreditLedgerEntry
from communications.services.gates import communications_billing_active
from communications.services.ledger import get_balances
from notifications.models import GuardianDelivery
from notifications.services.outbound import enqueue_guardian_email, enqueue_guardian_sms
from notifications.services.sms_status import (
    FINAL_STATUSES,
    NON_RESENDABLE,
    apply_provider_status,
)
from shared.services.arkesel_sms import extract_status_from_lookup, get_sms_status

logger = logging.getLogger(__name__)

SUCCESS_LIKE = frozenset({
    GuardianDelivery.Status.SUBMITTED,
    GuardianDelivery.Status.DELIVERED,
    GuardianDelivery.Status.SENT,
})


OVERVIEW_PERIODS = {
    '7d': 7,
    '30d': 30,
}

_SENT_STATUSES = [
    GuardianDelivery.Status.SUBMITTED,
    GuardianDelivery.Status.DELIVERED,
    GuardianDelivery.Status.SENT,
]


def _usage_between(school, start, end=None) -> dict:
    deliveries = GuardianDelivery.objects.filter(school=school, created_at__gte=start)
    if end is not None:
        deliveries = deliveries.filter(created_at__lt=end)
    aggregates = deliveries.aggregate(
        sms_sent=Count('id', filter=Q(channel='sms', status__in=_SENT_STATUSES)),
        sms_failed=Count('id', filter=Q(channel='sms', status=GuardianDelivery.Status.FAILED)),
        sms_skipped=Count('id', filter=Q(channel='sms', status=GuardianDelivery.Status.SKIPPED)),
        email_sent=Count('id', filter=Q(channel='email', status__in=_SENT_STATUSES)),
        email_failed=Count('id', filter=Q(channel='email', status=GuardianDelivery.Status.FAILED)),
        email_skipped=Count(
            'id',
            filter=Q(channel='email', status=GuardianDelivery.Status.SKIPPED),
        ),
    )
    credits_used = CreditLedgerEntry.objects.filter(
        school=school,
        entry_type=CreditLedgerEntry.EntryType.USAGE_DEBIT,
        occurred_at__gte=start,
    )
    if end is not None:
        credits_used = credits_used.filter(occurred_at__lt=end)
    credits_used = (
        credits_used
        .values('channel')
        .annotate(used=Sum('delta'))
    )
    used_by_channel = {
        row['channel']: abs(int(row['used'] or 0))
        for row in credits_used
    }
    by_event = []
    rows = (
        deliveries.values('channel', 'event_type')
        .annotate(
            sent=Count('id', filter=Q(status__in=_SENT_STATUSES)),
            failed=Count('id', filter=Q(status=GuardianDelivery.Status.FAILED)),
            skipped=Count('id', filter=Q(status=GuardianDelivery.Status.SKIPPED)),
            credits_used=Sum(F('credits_charged') - F('credits_refunded')),
        )
        .order_by('channel', 'event_type')
    )
    for row in rows:
        by_event.append({
            'channel': row['channel'],
            'event_type': row['event_type'],
            'sent': row['sent'] or 0,
            'failed': row['failed'] or 0,
            'skipped': row['skipped'] or 0,
            'credits_used': max(0, int(row['credits_used'] or 0)),
        })
    return {
        'sms_sent': aggregates['sms_sent'] or 0,
        'sms_failed': aggregates['sms_failed'] or 0,
        'sms_skipped': aggregates['sms_skipped'] or 0,
        'email_sent': aggregates['email_sent'] or 0,
        'email_failed': aggregates['email_failed'] or 0,
        'email_skipped': aggregates['email_skipped'] or 0,
        'sms_credits_used': used_by_channel.get('sms', 0),
        'email_credits_used': used_by_channel.get('email', 0),
        'by_event': by_event,
    }


def messaging_overview(school, period: str = '7d', start_date=None, end_date=None) -> dict:
    balances = get_balances(school)
    now = timezone.now()
    if start_date is not None or end_date is not None:
        if start_date is None or end_date is None:
            raise ValidationError({'detail': 'Choose both a start date and an end date.'})
        if end_date < start_date:
            raise ValidationError({'end': 'End date must be on or after the start date.'})
        if (end_date - start_date).days > 366:
            raise ValidationError({'end': 'Choose a range of one year or less.'})
        start = timezone.make_aware(datetime.combine(start_date, time.min))
        end = timezone.make_aware(datetime.combine(end_date + timedelta(days=1), time.min))
        usage = _usage_between(school, start, end)
        period_key = 'custom'
        period_start = start_date.isoformat()
        period_end = end_date.isoformat()
    else:
        days = OVERVIEW_PERIODS.get(period, 7)
        period_key = period if period in OVERVIEW_PERIODS else '7d'
        start = now - timedelta(days=days)
        usage = _usage_between(school, start)
        period_start = start.date().isoformat()
        period_end = now.date().isoformat()
    usage_7d = usage if period_key == '7d' else _usage_between(school, now - timedelta(days=7))
    open_failures = GuardianDelivery.objects.filter(
        school=school,
        status__in=[
            GuardianDelivery.Status.FAILED,
            GuardianDelivery.Status.UNKNOWN,
        ],
    ).count()

    return {
        'period': period_key,
        'period_start': period_start,
        'period_end': period_end,
        'credits': {
            'sms': balances.get('sms', 0),
            'email': balances.get('email', 0),
            'billing_active': communications_billing_active(school),
        },
        'usage': usage,
        'usage_7d': {key: value for key, value in usage_7d.items() if key != 'by_event'},
        'open_failures': open_failures,
    }


def delivery_queryset(school):
    return (
        GuardianDelivery.objects.filter(school=school)
        .select_related('parent', 'student', 'source_delivery')
        .order_by('-created_at')
    )


def apply_delivery_filters(qs, *, channel='', status='', event_type='', search=''):
    if channel:
        qs = qs.filter(channel=channel)
    if status:
        qs = qs.filter(status=status)
    if event_type:
        qs = qs.filter(event_type=event_type)
    if search:
        qs = qs.filter(
            Q(recipient_address__icontains=search) | Q(parent__name__icontains=search),
        )
    return qs


RESEND_SELECTION_LIMIT = 100


def eligible_resend_selection(
    school,
    *,
    channel='',
    status='',
    event_type='',
    search='',
) -> dict:
    """Failed or skipped messages with a body, matching the history filters.

    Returns at most ``RESEND_SELECTION_LIMIT`` rows, newest first — the same
    order as the history list.
    """
    qs = apply_delivery_filters(
        delivery_queryset(school),
        channel=channel,
        status=status,
        event_type=event_type,
        search=search,
    )
    qs = qs.filter(
        status__in=(GuardianDelivery.Status.FAILED, GuardianDelivery.Status.SKIPPED),
    ).alias(
        trimmed_text=Trim('body_text'),
        trimmed_preview=Trim('body_preview'),
    ).filter(
        Q(trimmed_text__gt='') | (Q(body_text='') & Q(trimmed_preview__gt='')),
    )
    total = qs.count()
    rows = list(qs.values('id', 'channel', 'segments')[:RESEND_SELECTION_LIMIT])
    items = []
    sms_credits = 0
    email_credits = 0
    for row in rows:
        segments = int(row['segments'] or 0)
        items.append({
            'id': row['id'],
            'channel': row['channel'],
            'segments': segments,
        })
        if row['channel'] == GuardianDelivery.Channel.SMS:
            sms_credits += max(1, segments or 1)
        elif row['channel'] == GuardianDelivery.Channel.EMAIL:
            email_credits += 1
    return {
        'total': total,
        'limit': RESEND_SELECTION_LIMIT,
        'capped': total > RESEND_SELECTION_LIMIT,
        'ids': [item['id'] for item in items],
        'items': items,
        'sms_credits': sms_credits,
        'email_credits': email_credits,
    }


def _delivery_for_school(*, school, delivery_id) -> GuardianDelivery:
    delivery = (
        GuardianDelivery.objects.filter(school=school, pk=delivery_id)
        .select_related('parent', 'student')
        .first()
    )
    if delivery is None:
        raise NotFound('Delivery not found.')
    return delivery


def verify_guardian_delivery(*, school, delivery_id) -> dict:
    """Poll Arkesel for an Unknown/non-final SMS before allowing resend."""
    delivery = _delivery_for_school(school=school, delivery_id=delivery_id)
    if delivery.channel != GuardianDelivery.Channel.SMS:
        raise ValidationError({'detail': 'Status verification is only available for SMS.'})

    if delivery.status in FINAL_STATUSES and delivery.status != GuardianDelivery.Status.UNKNOWN:
        return {
            'id': str(delivery.pk),
            'status': delivery.status,
            'can_resend': delivery.status == GuardianDelivery.Status.FAILED,
            'provider_status': delivery.provider_status,
            'verified': True,
        }

    if not delivery.provider_message_id:
        # Never submitted to Arkesel with an id — safe to treat as failed for resend.
        if delivery.status == GuardianDelivery.Status.UNKNOWN:
            delivery.status = GuardianDelivery.Status.FAILED
            delivery.user_error_message = (
                delivery.user_error_message
                or 'SMS submission could not be confirmed. You can resend.'
            )
            delivery.error_message = delivery.user_error_message
            delivery.status_updated_at = timezone.now()
            delivery.save(
                update_fields=[
                    'status',
                    'user_error_message',
                    'error_message',
                    'status_updated_at',
                    'updated_at',
                ],
            )
        return {
            'id': str(delivery.pk),
            'status': delivery.status,
            'can_resend': delivery.status == GuardianDelivery.Status.FAILED,
            'provider_status': delivery.provider_status,
            'verified': True,
        }

    try:
        payload = get_sms_status(delivery.provider_message_id)
        status_value = extract_status_from_lookup(payload)
        if status_value:
            delivery = apply_provider_status(
                sms_id=delivery.provider_message_id,
                provider_status=status_value,
                source='verify',
            ) or delivery
            delivery.refresh_from_db()
        else:
            raise ValidationError({
                'detail': 'Could not confirm SMS status with the provider. Try again shortly.',
            })
    except ValidationError:
        raise
    except Exception:
        logger.exception('Verify failed for delivery=%s', delivery.pk)
        raise ValidationError({
            'detail': 'Could not confirm SMS status with the provider. Try again shortly.',
        })

    return {
        'id': str(delivery.pk),
        'status': delivery.status,
        'can_resend': delivery.status == GuardianDelivery.Status.FAILED,
        'provider_status': delivery.provider_status,
        'verified': True,
    }


def retry_guardian_delivery(*, school, delivery_id, actor=None) -> dict:
    """Resend a Failed delivery as a new attempt (preserves original history)."""
    delivery = _delivery_for_school(school=school, delivery_id=delivery_id)

    if delivery.channel == GuardianDelivery.Channel.SMS:
        if delivery.status == GuardianDelivery.Status.UNKNOWN:
            verified = verify_guardian_delivery(school=school, delivery_id=delivery_id)
            delivery.refresh_from_db()
            if not verified.get('can_resend'):
                raise ValidationError({
                    'detail': (
                        f'Cannot resend while status is {delivery.status}. '
                        'Verification did not confirm failure.'
                    ),
                })
        if delivery.status in NON_RESENDABLE:
            raise ValidationError({
                'detail': f'Cannot resend a message with status “{delivery.status}”.',
            })
        if delivery.status not in (
            GuardianDelivery.Status.FAILED,
            GuardianDelivery.Status.SKIPPED,
        ):
            raise ValidationError({'detail': 'Only failed or skipped SMS messages can be resent.'})
    else:
        if delivery.status not in (
            GuardianDelivery.Status.FAILED,
            GuardianDelivery.Status.SKIPPED,
        ):
            raise ValidationError({'detail': 'Only failed or skipped emails can be retried.'})

    body = (delivery.body_text or delivery.body_preview or '').strip()
    if not body:
        raise ValidationError({'detail': 'Cannot resend: original message body is unavailable.'})

    new_key = f'retry:{delivery.pk}:{uuid4().hex[:12]}'
    base = {
        'school_id': str(school.pk),
        'parent_id': str(delivery.parent_id),
        'student_id': str(delivery.student_id) if delivery.student_id else None,
        'event_type': delivery.event_type,
        'recipient_address': delivery.recipient_address,
        'idempotency_key': new_key,
        'source_delivery_id': str(delivery.pk),
    }

    if delivery.channel == GuardianDelivery.Channel.SMS:
        queued = enqueue_guardian_sms([{**base, 'body': body}])
        channel = 'sms'
    else:
        queued = enqueue_guardian_email([
            {
                **base,
                'subject': f'Re: {delivery.event_type.replace("_", " ").title()}',
                'text_body': body,
                'html_body': f'<p>{body}</p>',
            },
        ])
        channel = 'email'

    return {
        'queued': queued,
        'channel': channel,
        'idempotency_key': new_key,
        'source_delivery_id': str(delivery.pk),
    }


def retry_guardian_deliveries(*, school, delivery_ids) -> dict:
    """Resend many eligible deliveries. Ineligible ids are reported, not fatal."""
    ids = list(dict.fromkeys(delivery_ids))
    if not ids:
        raise ValidationError({'ids': 'Select at least one message.'})
    if len(ids) > 100:
        raise ValidationError({'ids': 'Resend at most 100 messages at a time.'})

    queued = 0
    skipped = []
    for delivery_id in ids:
        try:
            result = retry_guardian_delivery(school=school, delivery_id=delivery_id)
        except ValidationError as exc:
            detail = exc.detail
            if isinstance(detail, dict):
                detail = detail.get('detail') or next(iter(detail.values()))
            if isinstance(detail, list):
                detail = detail[0]
            skipped.append({'id': str(delivery_id), 'detail': str(detail)})
            continue
        queued += int(result.get('queued') or 0)
    return {'queued': queued, 'skipped': skipped}
