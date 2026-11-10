from __future__ import annotations

import logging
from datetime import timedelta
from uuid import uuid4

from django.db.models import Count, Q, Sum
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


def messaging_overview(school) -> dict:
    balances = get_balances(school)
    since = timezone.now() - timedelta(days=7)
    deliveries = GuardianDelivery.objects.filter(school=school, created_at__gte=since)
    aggregates = deliveries.aggregate(
        sms_sent=Count(
            'id',
            filter=Q(
                channel='sms',
                status__in=[
                    GuardianDelivery.Status.SUBMITTED,
                    GuardianDelivery.Status.DELIVERED,
                    GuardianDelivery.Status.SENT,
                ],
            ),
        ),
        sms_failed=Count('id', filter=Q(channel='sms', status=GuardianDelivery.Status.FAILED)),
        sms_skipped=Count('id', filter=Q(channel='sms', status=GuardianDelivery.Status.SKIPPED)),
        email_sent=Count(
            'id',
            filter=Q(
                channel='email',
                status__in=[
                    GuardianDelivery.Status.SUBMITTED,
                    GuardianDelivery.Status.DELIVERED,
                    GuardianDelivery.Status.SENT,
                ],
            ),
        ),
        email_failed=Count(
            'id',
            filter=Q(channel='email', status=GuardianDelivery.Status.FAILED),
        ),
        email_skipped=Count(
            'id',
            filter=Q(channel='email', status=GuardianDelivery.Status.SKIPPED),
        ),
    )
    credits_used = (
        CreditLedgerEntry.objects.filter(
            school=school,
            entry_type=CreditLedgerEntry.EntryType.USAGE_DEBIT,
            occurred_at__gte=since,
        )
        .values('channel')
        .annotate(used=Sum('delta'))
    )
    used_by_channel = {
        row['channel']: abs(int(row['used'] or 0))
        for row in credits_used
    }
    open_failures = GuardianDelivery.objects.filter(
        school=school,
        status__in=[
            GuardianDelivery.Status.FAILED,
            GuardianDelivery.Status.UNKNOWN,
        ],
    ).count()

    return {
        'credits': {
            'sms': balances.get('sms', 0),
            'email': balances.get('email', 0),
            'billing_active': communications_billing_active(school),
        },
        'usage_7d': {
            'sms_sent': aggregates['sms_sent'] or 0,
            'sms_failed': aggregates['sms_failed'] or 0,
            'sms_skipped': aggregates['sms_skipped'] or 0,
            'email_sent': aggregates['email_sent'] or 0,
            'email_failed': aggregates['email_failed'] or 0,
            'email_skipped': aggregates['email_skipped'] or 0,
            'sms_credits_used': used_by_channel.get('sms', 0),
            'email_credits_used': used_by_channel.get('email', 0),
        },
        'open_failures': open_failures,
    }


def delivery_queryset(school):
    return (
        GuardianDelivery.objects.filter(school=school)
        .select_related('parent', 'student', 'source_delivery')
        .order_by('-created_at')
    )


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
        if delivery.status != GuardianDelivery.Status.FAILED:
            raise ValidationError({'detail': 'Only failed SMS messages can be resent.'})
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
