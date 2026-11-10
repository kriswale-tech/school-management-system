"""Arkesel SMS client — single and batched sends (max 100 recipients per request)."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass

import requests
from django.conf import settings
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import SSLError, Timeout

logger = logging.getLogger(__name__)

ARKESEL_SMS_SEND_URL = 'https://sms.arkesel.com/api/v2/sms/send'
ARKESEL_SMS_STATUS_URL = 'https://sms.arkesel.com/api/v2/sms/{message_id}'
ARKESEL_SMS_BATCH_SIZE = 100


@dataclass
class ArkeselOutcome:
    """Normalized send result for one recipient attempt."""

    ok: bool
    outcome: str  # submitted | failed | unknown
    user_message: str = ''
    provider_message_id: str = ''
    response: dict | None = None
    error: str = ''
    status_code: int | None = None


def _headers() -> dict:
    return {
        'api-key': settings.ARKESEL_API_KEY,
        'Content-Type': 'application/json',
    }


def _sandbox_flag(sandbox: bool | None) -> bool:
    return settings.DEBUG if sandbox is None else sandbox


def arkesel_callback_url() -> str:
    """Public DLR webhook URL passed as ``callback_url`` on send."""
    base = (getattr(settings, 'PUBLIC_BASE_URL', None) or '').rstrip('/')
    if not base:
        return ''
    return f'{base}/api/v1/webhooks/arkesel/sms-dlr/'


def classify_arkesel_http_error(status_code: int | None, body_text: str = '') -> ArkeselOutcome:
    """Map HTTP failures to user-safe messages (technical detail stays in logs)."""
    snippet = (body_text or '')[:300]
    if status_code == 401:
        user = 'SMS service authentication failed. Please contact support.'
        outcome = 'failed'
    elif status_code == 422:
        user = 'The SMS could not be accepted. Check the phone number and try again.'
        outcome = 'failed'
    elif status_code == 429:
        user = 'SMS sending is temporarily rate-limited. Please try again shortly.'
        outcome = 'failed'
    elif status_code is not None and status_code >= 500:
        user = 'The SMS provider is temporarily unavailable. Please try again later.'
        outcome = 'failed'
    else:
        user = 'The SMS could not be sent. Please try again.'
        outcome = 'failed'
    return ArkeselOutcome(
        ok=False,
        outcome=outcome,
        user_message=user,
        error=f'HTTP {status_code}: {snippet}',
        status_code=status_code,
    )


def classify_arkesel_transport_error(exc: Exception) -> ArkeselOutcome:
    """Timeouts / SSL / connection issues → Unknown (submission not confirmed)."""
    if isinstance(exc, Timeout):
        user = 'The SMS provider did not respond in time. Delivery status is unconfirmed.'
    elif isinstance(exc, SSLError):
        user = 'A secure connection to the SMS provider could not be established.'
    elif isinstance(exc, RequestsConnectionError):
        user = 'Could not reach the SMS provider. Delivery status is unconfirmed.'
    else:
        user = 'SMS submission could not be confirmed.'
    return ArkeselOutcome(
        ok=False,
        outcome='unknown',
        user_message=user,
        error=f'{type(exc).__name__}: {exc}'[:500],
    )


def send_sms(phone_number: str, message: str, *, sandbox: bool | None = None) -> dict:
    """Send one SMS via Arkesel."""
    return send_sms_to_recipients(
        [phone_number],
        message,
        sandbox=sandbox,
    )


def send_sms_to_recipients(
    recipients: list[str],
    message: str,
    *,
    sandbox: bool | None = None,
    callback_url: str | None = None,
) -> dict:
    """Send the same message to up to 100 recipients in one Arkesel request."""
    cleaned = [str(phone).strip() for phone in recipients if str(phone).strip()]
    if not cleaned:
        raise ValueError('At least one recipient is required.')
    if len(cleaned) > ARKESEL_SMS_BATCH_SIZE:
        raise ValueError(
            f'Arkesel accepts at most {ARKESEL_SMS_BATCH_SIZE} recipients per request.',
        )

    payload = {
        'sender': settings.ARKESEL_SMS_SENDER,
        'message': message,
        'recipients': cleaned,
        'sandbox': _sandbox_flag(sandbox),
    }
    cb = callback_url if callback_url is not None else arkesel_callback_url()
    if cb:
        payload['callback_url'] = cb

    response = requests.post(
        ARKESEL_SMS_SEND_URL,
        json=payload,
        headers=_headers(),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _provider_id_from_entry(entry) -> str:
    if isinstance(entry, dict):
        return str(
            entry.get('id')
            or entry.get('message_id')
            or entry.get('sms_id')
            or '',
        )
    return str(entry or '')


def send_personalized_sms_batch(
    items: list[dict],
    *,
    sandbox: bool | None = None,
) -> list[dict]:
    """Send personalized SMS messages, batching identical bodies up to 100 recipients.

    Each item: ``{'phone': str, 'message': str, 'key': str}``.
    Returns one result dict per input item with keys:
    ``key``, ``phone``, ``ok``, ``outcome``, ``user_message``,
    ``provider_message_id``, ``response`` / ``error``.
    """
    results_by_key: dict[str, dict] = {}
    groups: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        phone = str(item.get('phone') or '').strip()
        message = str(item.get('message') or '')
        key = str(item.get('key') or '')
        if not phone or not message or not key:
            results_by_key[key or phone] = {
                'key': key,
                'phone': phone,
                'ok': False,
                'outcome': 'failed',
                'user_message': 'Missing phone number or message content.',
                'error': 'Missing phone, message, or key',
            }
            continue
        groups[message].append({'phone': phone, 'key': key})

    for message, group in groups.items():
        for start in range(0, len(group), ARKESEL_SMS_BATCH_SIZE):
            chunk = group[start:start + ARKESEL_SMS_BATCH_SIZE]
            phones = [row['phone'] for row in chunk]
            try:
                response = send_sms_to_recipients(phones, message, sandbox=sandbox)
                data = response.get('data') if isinstance(response, dict) else None
                for index, row in enumerate(chunk):
                    provider_id = ''
                    if isinstance(data, list) and index < len(data):
                        provider_id = _provider_id_from_entry(data[index])
                    elif isinstance(data, dict):
                        provider_id = _provider_id_from_entry(data)
                    if not provider_id and isinstance(response, dict):
                        provider_id = str(response.get('message_id') or '')
                    results_by_key[row['key']] = {
                        'key': row['key'],
                        'phone': row['phone'],
                        'ok': True,
                        'outcome': 'submitted',
                        'user_message': '',
                        'response': response,
                        'provider_message_id': provider_id,
                    }
            except requests.HTTPError as exc:
                status_code = getattr(exc.response, 'status_code', None)
                body_text = ''
                try:
                    body_text = exc.response.text if exc.response is not None else ''
                except Exception:
                    body_text = ''
                logger.exception(
                    'Arkesel SMS HTTP error status=%s body=%s recipients=%s',
                    status_code,
                    body_text[:500],
                    len(phones),
                )
                outcome = classify_arkesel_http_error(status_code, body_text)
                for row in chunk:
                    results_by_key[row['key']] = {
                        'key': row['key'],
                        'phone': row['phone'],
                        'ok': False,
                        'outcome': outcome.outcome,
                        'user_message': outcome.user_message,
                        'error': outcome.error,
                        'status_code': outcome.status_code,
                    }
            except (Timeout, SSLError, RequestsConnectionError) as exc:
                logger.exception(
                    'Arkesel SMS transport error recipients=%s: %s',
                    len(phones),
                    exc,
                )
                outcome = classify_arkesel_transport_error(exc)
                for row in chunk:
                    results_by_key[row['key']] = {
                        'key': row['key'],
                        'phone': row['phone'],
                        'ok': False,
                        'outcome': outcome.outcome,
                        'user_message': outcome.user_message,
                        'error': outcome.error,
                    }
            except Exception as exc:
                logger.exception('Arkesel SMS unexpected error recipients=%s', len(phones))
                outcome = classify_arkesel_transport_error(exc)
                for row in chunk:
                    results_by_key[row['key']] = {
                        'key': row['key'],
                        'phone': row['phone'],
                        'ok': False,
                        'outcome': 'unknown',
                        'user_message': outcome.user_message,
                        'error': f'{type(exc).__name__}: {exc}'[:500],
                    }

    ordered = []
    for item in items:
        key = str(item.get('key') or '')
        ordered.append(
            results_by_key.get(
                key,
                {
                    'key': key,
                    'phone': str(item.get('phone') or ''),
                    'ok': False,
                    'outcome': 'failed',
                    'user_message': 'The SMS could not be sent.',
                    'error': 'No result',
                },
            ),
        )
    return ordered


def get_sms_status(message_id: str) -> dict:
    """Fetch delivery status for a previously sent Arkesel message."""
    response = requests.get(
        ARKESEL_SMS_STATUS_URL.format(message_id=message_id),
        headers=_headers(),
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def extract_status_from_lookup(payload: dict) -> str:
    """Best-effort parse of Arkesel status lookup JSON."""
    if not isinstance(payload, dict):
        return ''
    for key in ('status', 'delivery_status', 'sms_status'):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().upper()
    data = payload.get('data')
    if isinstance(data, dict):
        for key in ('status', 'delivery_status', 'sms_status'):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().upper()
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            for key in ('status', 'delivery_status', 'sms_status'):
                value = first.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip().upper()
    return ''
