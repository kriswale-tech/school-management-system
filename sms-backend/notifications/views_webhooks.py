"""Unauthenticated provider webhooks (Arkesel SMS DLR, SES / legacy Resend email)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from communications.services.providers import (
    get_provider_account,
    mark_webhook_received,
    mark_webhook_signature_failure,
)
from communications.models import Provider
from notifications.services.email_status import (
    apply_resend_event,
    apply_ses_event,
    extract_event_type,
    extract_ses_event_type,
    extract_ses_message_id,
    record_webhook_event,
)
from notifications.services.sms_status import apply_provider_status

logger = logging.getLogger(__name__)

# Svix tolerates a 5 minute clock skew on the signed timestamp.
SVIX_TIMESTAMP_TOLERANCE_SECONDS = 5 * 60


@method_decorator(csrf_exempt, name='dispatch')
class ArkeselSmsDlrWebhookView(APIView):
    """Arkesel delivery callback.

    Docs: pass ``callback_url`` on send; Arkesel calls with query params
    ``sms_id`` and ``status`` (DELIVERED, SUBMITTED, QUEUED, NOT_DELIVERED, …).
    Endpoint must stay public (no auth). Match ``sms_id`` to our records only.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return self._handle(request)

    def post(self, request):
        return self._handle(request)

    def _handle(self, request):
        sms_id = (
            request.query_params.get('sms_id')
            or request.data.get('sms_id')
            or ''
        )
        status_value = (
            request.query_params.get('status')
            or request.data.get('status')
            or ''
        )
        if not sms_id or not status_value:
            # Still 200 so Arkesel does not hammer retries on malformed noise.
            return Response({'received': True, 'updated': False}, status=200)

        delivery = apply_provider_status(
            sms_id=str(sms_id),
            provider_status=str(status_value),
            source='webhook',
        )
        return Response(
            {
                'received': True,
                'updated': delivery is not None,
                'status': delivery.status if delivery else None,
            },
            status=200,
        )


def _verify_svix_signature(*, body: bytes, headers, secret: str) -> bool:
    """Verify Resend/Svix webhook signature.

    Headers: ``svix-id``, ``svix-timestamp``, ``svix-signature`` (space-delimited
    ``v1,<base64>`` variants). Secret may be ``whsec_…`` base64 payload.
    """
    msg_id = headers.get('svix-id') or headers.get('Svix-Id') or ''
    timestamp = headers.get('svix-timestamp') or headers.get('Svix-Timestamp') or ''
    signature_header = headers.get('svix-signature') or headers.get('Svix-Signature') or ''
    if not msg_id or not timestamp or not signature_header:
        return False
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs(int(time.time()) - ts) > SVIX_TIMESTAMP_TOLERANCE_SECONDS:
        return False

    secret_bytes = secret.encode('utf-8')
    if secret.startswith('whsec_'):
        try:
            secret_bytes = base64.b64decode(secret[len('whsec_'):])
        except Exception:
            secret_bytes = secret.encode('utf-8')

    to_sign = f'{msg_id}.{timestamp}.'.encode('utf-8') + body
    digest = base64.b64encode(hmac.new(secret_bytes, to_sign, hashlib.sha256).digest()).decode()
    expected = f'v1,{digest}'
    candidates = [part.strip() for part in signature_header.split(' ') if part.strip()]
    return any(hmac.compare_digest(candidate, expected) for candidate in candidates)


@method_decorator(csrf_exempt, name='dispatch')
class SesWebhookView(APIView):
    """Amazon SES → SNS notification webhook (placeholder-friendly).

    Until AWS is wired:
    - Accepts JSON SNS envelopes (``SubscriptionConfirmation``, ``Notification``)
      and raw SES event payloads for local testing.
    - Auth is optional shared token via ``SES_WEBHOOK_AUTH_TOKEN``
      (query ``?token=`` or ``X-SES-Webhook-Token`` header).
    - SNS signature verification is intentionally deferred; do not expose this
      publicly without the token until AWS confirmation is complete.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw = request.body or b''
        token = (getattr(settings, 'SES_WEBHOOK_AUTH_TOKEN', '') or '').strip()
        provided = (
            request.query_params.get('token')
            or request.headers.get('X-SES-Webhook-Token')
            or request.headers.get('x-ses-webhook-token')
            or ''
        ).strip()
        signature_valid = False

        if token:
            if not provided or not hmac.compare_digest(provided, token):
                try:
                    account = get_provider_account(provider=Provider.SES, channel='email')
                    mark_webhook_signature_failure(account)
                except Exception:
                    logger.exception('Failed to record SES webhook auth failure')
                return Response({'detail': 'Invalid webhook token.'}, status=401)
            signature_valid = True
        elif not settings.DEBUG:
            return Response({'detail': 'SES webhook token not configured.'}, status=503)
        else:
            logger.warning('SES webhook accepted without token verification (DEBUG).')
            signature_valid = True

        try:
            payload = json.loads(raw.decode('utf-8') or '{}')
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = request.data if isinstance(request.data, dict) else {}

        if not isinstance(payload, dict):
            payload = {}

        # SNS subscription handshake — acknowledge so AWS can confirm.
        sns_type = str(payload.get('Type') or '').strip()
        if sns_type == 'SubscriptionConfirmation':
            logger.info(
                'SES SNS SubscriptionConfirmation received (subscribe_url present=%s)',
                bool(payload.get('SubscribeURL')),
            )
            return Response(
                {
                    'received': True,
                    'sns_type': sns_type,
                    'note': (
                        'Confirm the subscription in AWS (or GET SubscribeURL). '
                        'This stub does not auto-confirm.'
                    ),
                },
                status=200,
            )

        event_payload = payload
        if sns_type == 'Notification' and isinstance(payload.get('Message'), str):
            try:
                event_payload = json.loads(payload['Message'])
            except json.JSONDecodeError:
                event_payload = {'raw_message': payload.get('Message')}

        event_type = extract_ses_event_type(event_payload)
        message_id = extract_ses_message_id(event_payload)
        mail = event_payload.get('mail') if isinstance(event_payload, dict) else None
        mail_message_id = ''
        if isinstance(mail, dict):
            mail_message_id = str(mail.get('messageId') or '')
        event_id = str(
            payload.get('MessageId')
            or mail_message_id
            or message_id
            or '',
        )
        if not event_id:
            event_id = hashlib.sha256(
                raw or json.dumps(payload, sort_keys=True, default=str).encode(),
            ).hexdigest()

        row, created = record_webhook_event(
            event_id=str(event_id)[:191],
            event_type=event_type or 'ses.notification',
            payload=event_payload if isinstance(event_payload, dict) else {},
            signature_valid=signature_valid,
        )
        if not created and row.processed:
            return Response({'received': True, 'duplicate': True, 'processed': True}, status=200)

        outcome = apply_ses_event(
            event_type=event_type,
            payload=event_payload if isinstance(event_payload, dict) else {},
            message_id=message_id,
        )
        row.processed = True
        row.matched_delivery_type = outcome.get('matched_type') or ''
        row.matched_delivery_id = str(outcome.get('matched_id') or '')
        if message_id and not row.provider_message_id:
            row.provider_message_id = message_id[:100]
        row.save(
            update_fields=[
                'processed',
                'matched_delivery_type',
                'matched_delivery_id',
                'provider_message_id',
                'updated_at',
            ],
        )
        try:
            account = get_provider_account(provider=Provider.SES, channel='email')
            mark_webhook_received(account)
        except Exception:
            logger.exception('Failed to mark SES webhook received')

        return Response(
            {
                'received': True,
                'duplicate': not created,
                'processed': True,
                'matched_type': outcome.get('matched_type'),
                'matched_id': outcome.get('matched_id'),
                'status': outcome.get('status'),
                'refunded': outcome.get('refunded'),
                'placeholder': not bool(
                    (getattr(settings, 'AWS_ACCESS_KEY_ID', '') or '').strip(),
                ),
            },
            status=200,
        )


@method_decorator(csrf_exempt, name='dispatch')
class ResendWebhookView(APIView):
    """Legacy Resend email lifecycle webhook (Svix-signed). Kept for history."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw = request.body or b''
        secret = (getattr(settings, 'RESEND_WEBHOOK_SECRET', '') or '').strip()
        signature_valid = False

        if secret:
            signature_valid = _verify_svix_signature(
                body=raw,
                headers=request.headers,
                secret=secret,
            )
            if not signature_valid:
                try:
                    account = get_provider_account(provider=Provider.RESEND, channel='email')
                    mark_webhook_signature_failure(account)
                except Exception:
                    logger.exception('Failed to record Resend signature failure')
                return Response({'detail': 'Invalid signature.'}, status=401)
        elif not settings.DEBUG:
            return Response({'detail': 'Webhook secret not configured.'}, status=503)
        else:
            logger.warning('Resend webhook accepted without signature verification (DEBUG).')
            signature_valid = True

        try:
            payload = json.loads(raw.decode('utf-8') or '{}')
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = request.data if isinstance(request.data, dict) else {}

        event_type = extract_event_type(payload)
        event_id = (
            request.headers.get('svix-id')
            or request.headers.get('Svix-Id')
            or payload.get('id')
            or ''
        )
        if not event_id:
            event_id = hashlib.sha256(raw or json.dumps(payload, sort_keys=True).encode()).hexdigest()

        row, created = record_webhook_event(
            event_id=str(event_id)[:191],
            event_type=event_type,
            payload=payload if isinstance(payload, dict) else {},
            signature_valid=signature_valid,
        )
        if not created and row.processed:
            return Response({'received': True, 'duplicate': True, 'processed': True}, status=200)

        outcome = apply_resend_event(event_type=event_type, payload=payload)
        row.processed = True
        row.matched_delivery_type = outcome.get('matched_type') or ''
        row.matched_delivery_id = str(outcome.get('matched_id') or '')
        row.save(
            update_fields=[
                'processed',
                'matched_delivery_type',
                'matched_delivery_id',
                'updated_at',
            ],
        )
        try:
            account = get_provider_account(provider=Provider.RESEND, channel='email')
            mark_webhook_received(account)
        except Exception:
            logger.exception('Failed to mark Resend webhook received')

        return Response(
            {
                'received': True,
                'duplicate': not created,
                'processed': True,
                'matched_type': outcome.get('matched_type'),
                'matched_id': outcome.get('matched_id'),
                'status': outcome.get('status'),
                'refunded': outcome.get('refunded'),
            },
            status=200,
        )
