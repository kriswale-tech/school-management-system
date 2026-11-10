"""Record platform-funded outbound traffic (v4.1 §2.6.5).

Purpose: make the provider cost of OTP SMS, OTP email, and staff notification
email VISIBLE without ever touching a school wallet. Every function here is
best-effort — a logging failure must never break an OTP or a notification.

v4 invariant 4 is enforced structurally: ``CreditLedgerEntry`` has no foreign
key to ``PlatformOutboundDelivery``, so these rows cannot carry a usage debit.
"""

from __future__ import annotations

import hashlib
import logging
from uuid import uuid4

from django.db import IntegrityError, transaction
from django.utils import timezone

from notifications.models import BillingClassification, PlatformOutboundDelivery

logger = logging.getLogger(__name__)


def _snapshot(*, channel: str, body: str, units: int) -> dict:
    try:
        from communications.services.pricing import snapshot_for_channel

        snapshot = snapshot_for_channel(channel=channel, body=body, units=units)
        return {
            'provider_cost_snapshot_ghs': snapshot.get('provider_cost_snapshot_ghs'),
            'encoding_snapshot': snapshot.get('encoding_snapshot') or '',
            'segment_limit_snapshot': snapshot.get('segment_limit_snapshot') or {},
        }
    except Exception:
        logger.debug('Could not snapshot platform outbound cost', exc_info=True)
        return {
            'provider_cost_snapshot_ghs': None,
            'encoding_snapshot': '',
            'segment_limit_snapshot': {},
        }


def _default_key(*, purpose: str, channel: str, recipient: str) -> str:
    """Stable-ish key that does not store a bare phone/email twice over."""
    digest = hashlib.sha256(f'{recipient}'.encode()).hexdigest()[:16]
    return f'platform:{purpose}:{channel}:{digest}:{uuid4().hex[:10]}'


def record_platform_outbound(
    *,
    purpose: str,
    channel: str,
    provider: str = PlatformOutboundDelivery.Provider.OTHER,
    status: str = PlatformOutboundDelivery.Status.SUBMITTED,
    school=None,
    recipient_address: str = '',
    provider_message_id: str = '',
    body: str = '',
    units: int | None = None,
    idempotency_key: str | None = None,
    error_message: str = '',
    metadata: dict | None = None,
) -> PlatformOutboundDelivery | None:
    """Append one platform-funded delivery row. Returns ``None`` on any failure."""
    try:
        if channel == PlatformOutboundDelivery.Channel.SMS:
            from communications.services.segments import sms_segment_count

            segments = max(1, sms_segment_count(body or ''))
            resolved_units = int(units or segments)
        else:
            segments = 0
            resolved_units = int(units or 1)

        snapshot = _snapshot(channel=channel, body=body or '', units=resolved_units)
        key = idempotency_key or _default_key(
            purpose=purpose,
            channel=channel,
            recipient=recipient_address,
        )

        with transaction.atomic():
            return PlatformOutboundDelivery.objects.create(
                school=school,
                purpose=purpose,
                channel=channel,
                provider=provider,
                status=status,
                recipient_address=(recipient_address or '')[:255],
                provider_message_id=(provider_message_id or '')[:100],
                segments=segments,
                units=resolved_units,
                billing_classification=BillingClassification.FREE,
                error_message=(error_message or '')[:500],
                idempotency_key=key[:191],
                metadata=metadata or {},
                status_updated_at=timezone.now(),
                **snapshot,
            )
    except IntegrityError:
        return PlatformOutboundDelivery.objects.filter(
            idempotency_key=(idempotency_key or '')[:191],
        ).first()
    except Exception:
        # Never let visibility logging break the thing it is observing.
        logger.exception('Failed to record platform outbound delivery (%s/%s)', purpose, channel)
        return None


def arkesel_message_id(payload) -> str:
    """Best-effort provider id from an Arkesel send response."""
    if not isinstance(payload, dict):
        return ''
    if payload.get('message_id'):
        return str(payload['message_id'])
    data = payload.get('data')
    candidates = []
    if isinstance(data, list) and data and isinstance(data[0], dict):
        candidates.append(data[0])
    if isinstance(data, dict):
        candidates.append(data)
    for source in candidates:
        for key in ('id', 'message_id', 'sms_id'):
            if source.get(key):
                return str(source[key])
    return ''


def record_otp_sms(*, phone_number: str, body: str, provider_payload=None, ok: bool = True):
    return record_platform_outbound(
        purpose=PlatformOutboundDelivery.Purpose.OTP_SMS,
        channel=PlatformOutboundDelivery.Channel.SMS,
        provider=PlatformOutboundDelivery.Provider.ARKESEL,
        status=(
            PlatformOutboundDelivery.Status.SUBMITTED
            if ok
            else PlatformOutboundDelivery.Status.FAILED
        ),
        recipient_address=phone_number,
        provider_message_id=arkesel_message_id(provider_payload),
        body=body,
    )


def record_otp_email(*, email: str, ok: bool = True, error_message: str = ''):
    return record_platform_outbound(
        purpose=PlatformOutboundDelivery.Purpose.OTP_EMAIL,
        channel=PlatformOutboundDelivery.Channel.EMAIL,
        provider=PlatformOutboundDelivery.Provider.SES,
        status=(
            PlatformOutboundDelivery.Status.SUBMITTED
            if ok
            else PlatformOutboundDelivery.Status.FAILED
        ),
        recipient_address=email,
        error_message=error_message,
    )


def record_staff_email(*, notification, email: str, ok: bool = True, error_message: str = ''):
    return record_platform_outbound(
        purpose=PlatformOutboundDelivery.Purpose.STAFF_EMAIL,
        channel=PlatformOutboundDelivery.Channel.EMAIL,
        provider=PlatformOutboundDelivery.Provider.SES,
        status=(
            PlatformOutboundDelivery.Status.SUBMITTED
            if ok
            else PlatformOutboundDelivery.Status.FAILED
        ),
        school=getattr(notification, 'school', None),
        recipient_address=email,
        idempotency_key=f'platform:staff_email:{notification.pk}',
        error_message=error_message,
        metadata={'event_type': getattr(notification, 'event_type', '')},
    )
