"""Arkesel SMS client — single and batched sends (max 100 recipients per request)."""

from __future__ import annotations

from collections import defaultdict

import requests
from django.conf import settings

ARKESEL_SMS_SEND_URL = 'https://sms.arkesel.com/api/v2/sms/send'
ARKESEL_SMS_STATUS_URL = 'https://sms.arkesel.com/api/v2/sms/{message_id}'
ARKESEL_SMS_BATCH_SIZE = 100


def _headers() -> dict:
    return {
        'api-key': settings.ARKESEL_API_KEY,
        'Content-Type': 'application/json',
    }


def _sandbox_flag(sandbox: bool | None) -> bool:
    return settings.DEBUG if sandbox is None else sandbox


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
    response = requests.post(
        ARKESEL_SMS_SEND_URL,
        json=payload,
        headers=_headers(),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def send_personalized_sms_batch(
    items: list[dict],
    *,
    sandbox: bool | None = None,
) -> list[dict]:
    """Send personalized SMS messages, batching identical bodies up to 100 recipients.

    Each item: ``{'phone': str, 'message': str, 'key': str}``.
    Returns one result dict per input item (same order) with keys:
    ``key``, ``phone``, ``ok``, ``response`` / ``error``.
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
                        entry = data[index]
                        if isinstance(entry, dict):
                            provider_id = str(
                                entry.get('id')
                                or entry.get('message_id')
                                or entry.get('sms_id')
                                or '',
                            )
                        else:
                            provider_id = str(entry or '')
                    elif isinstance(data, dict):
                        provider_id = str(
                            data.get('id')
                            or data.get('message_id')
                            or data.get('sms_id')
                            or '',
                        )
                    if not provider_id and isinstance(response, dict):
                        provider_id = str(response.get('message_id') or '')
                    results_by_key[row['key']] = {
                        'key': row['key'],
                        'phone': row['phone'],
                        'ok': True,
                        'response': response,
                        'provider_message_id': provider_id,
                    }
            except Exception as exc:
                for row in chunk:
                    results_by_key[row['key']] = {
                        'key': row['key'],
                        'phone': row['phone'],
                        'ok': False,
                        'error': str(exc)[:500],
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
