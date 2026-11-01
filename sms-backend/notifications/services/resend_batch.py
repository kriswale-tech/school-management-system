"""Resend batch email API (up to 100 emails per request)."""

from __future__ import annotations

import logging

import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)

RESEND_BATCH_URL = 'https://api.resend.com/emails/batch'
RESEND_EMAIL_BATCH_SIZE = 100


def _from_email() -> str:
    return settings.DEFAULT_FROM_EMAIL


def _resend_api_key() -> str:
    return (getattr(settings, 'RESEND_API_KEY', None) or '').strip()


def _use_resend_http() -> bool:
    return bool(getattr(settings, 'EMAIL_ENABLED', False) and _resend_api_key())


def send_email_batch(items: list[dict]) -> list[dict]:
    """Send up to 100 emails.

    Each item: ``to``, ``subject``, ``text``, ``html``, ``key``.
    Returns one result per item: ``key``, ``ok``, ``provider_message_id`` / ``error``.
    """
    if len(items) > RESEND_EMAIL_BATCH_SIZE:
        raise ValueError(
            f'Resend accepts at most {RESEND_EMAIL_BATCH_SIZE} emails per batch.',
        )
    if not items:
        return []

    if not _use_resend_http():
        return _send_via_django(items)

    payload = []
    for item in items:
        payload.append({
            'from': _from_email(),
            'to': [str(item['to']).strip()],
            'subject': item['subject'],
            'text': item.get('text') or '',
            'html': item.get('html') or '',
        })

    try:
        response = requests.post(
            RESEND_BATCH_URL,
            json=payload,
            headers={
                'Authorization': f'Bearer {_resend_api_key()}',
                'Content-Type': 'application/json',
                # Allow partial success so one bad address does not fail the batch.
                'x-batch-validation': 'permissive',
            },
            timeout=60,
        )
        response.raise_for_status()
        body = response.json()
    except Exception as exc:
        logger.exception('Resend batch request failed')
        return [
            {
                'key': item.get('key', ''),
                'ok': False,
                'error': str(exc)[:500],
            }
            for item in items
        ]

    data = body.get('data') if isinstance(body, dict) else None
    errors = body.get('errors') if isinstance(body, dict) else None
    error_by_index: dict[int, str] = {}
    if isinstance(errors, list):
        for entry in errors:
            if not isinstance(entry, dict):
                continue
            index = entry.get('index')
            if isinstance(index, int):
                error_by_index[index] = str(entry.get('message') or 'Batch email failed')[:500]

    results = []
    for index, item in enumerate(items):
        if index in error_by_index:
            results.append({
                'key': item.get('key', ''),
                'ok': False,
                'error': error_by_index[index],
            })
            continue
        provider_id = ''
        if isinstance(data, list) and index < len(data) and isinstance(data[index], dict):
            provider_id = str(data[index].get('id') or '')
        results.append({
            'key': item.get('key', ''),
            'ok': True,
            'provider_message_id': provider_id,
        })
    return results


def _send_via_django(items: list[dict]) -> list[dict]:
    """Console / locmem / Anymail single-send fallback when Resend HTTP is off."""
    results = []
    for item in items:
        key = item.get('key', '')
        try:
            message = EmailMultiAlternatives(
                subject=item['subject'],
                body=item.get('text') or '',
                from_email=_from_email(),
                to=[str(item['to']).strip()],
            )
            html = item.get('html') or ''
            if html:
                message.attach_alternative(html, 'text/html')
            message.send(fail_silently=False)
            results.append({'key': key, 'ok': True, 'provider_message_id': ''})
        except Exception as exc:
            logger.exception('Guardian email fallback send failed for %s', key)
            results.append({'key': key, 'ok': False, 'error': str(exc)[:500]})
    return results
