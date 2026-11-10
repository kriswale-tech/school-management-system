"""Outbound email batch send — Amazon SES with safe console fallback.

``EMAIL_PROVIDER=ses`` uses boto3 when AWS credentials are present.
Without credentials (or ``EMAIL_PROVIDER=console`` / ``EMAIL_ENABLED=false``),
sends go through Django's configured mail backend (console/locmem in dev/tests)
so the full guardian + staff flows can be exercised before any AWS account exists.
"""

from __future__ import annotations

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)

EMAIL_BATCH_SIZE = 100


def _from_email() -> str:
    return settings.DEFAULT_FROM_EMAIL


def _provider() -> str:
    return (getattr(settings, 'EMAIL_PROVIDER', 'ses') or 'ses').strip().lower()


def ses_configured() -> bool:
    """True when we have enough config to attempt a real SES API call."""
    if not getattr(settings, 'EMAIL_ENABLED', False):
        return False
    if _provider() != 'ses':
        return False
    key = (getattr(settings, 'AWS_ACCESS_KEY_ID', None) or '').strip()
    secret = (getattr(settings, 'AWS_SECRET_ACCESS_KEY', None) or '').strip()
    region = (getattr(settings, 'AWS_REGION', None) or '').strip()
    return bool(key and secret and region)


def _use_live_ses() -> bool:
    return ses_configured()


def send_email_batch(items: list[dict]) -> list[dict]:
    """Send up to 100 emails.

    Each item: ``to``, ``subject``, ``text``, ``html``, ``key``.
    Returns one result per item: ``key``, ``ok``, ``provider_message_id`` / ``error``.
    """
    if len(items) > EMAIL_BATCH_SIZE:
        raise ValueError(f'Email batch accepts at most {EMAIL_BATCH_SIZE} emails.')
    if not items:
        return []

    if _use_live_ses():
        return _send_via_ses(items)

    if _provider() == 'ses' and getattr(settings, 'EMAIL_ENABLED', False):
        logger.warning(
            'EMAIL_PROVIDER=ses but AWS credentials/region are incomplete; '
            'falling back to Django mail backend (console/locmem).',
        )
    return _send_via_django(items)


def _send_via_django(items: list[dict]) -> list[dict]:
    """Console / locmem / configured Django backend — used for local/placeholder mode."""
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
            # Placeholder id so downstream rows still look "provider accepted".
            results.append({
                'key': key,
                'ok': True,
                'provider_message_id': f'console-{key}'[:100] if key else 'console',
            })
        except Exception as exc:
            logger.exception('Guardian email fallback send failed for %s', key)
            results.append({'key': key, 'ok': False, 'error': str(exc)[:500]})
    return results


def _ses_client():
    import boto3

    return boto3.client(
        'ses',
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def _send_via_ses(items: list[dict]) -> list[dict]:
    """Send each message with SES SendRawEmail (HTML + text)."""
    try:
        client = _ses_client()
    except Exception as exc:
        logger.exception('Failed to create SES client')
        return [
            {'key': item.get('key', ''), 'ok': False, 'error': str(exc)[:500]}
            for item in items
        ]

    results = []
    for item in items:
        key = item.get('key', '')
        to_addr = str(item['to']).strip()
        try:
            raw = _build_raw_message(
                to_addr=to_addr,
                subject=item['subject'],
                text=item.get('text') or '',
                html=item.get('html') or '',
            )
            response = client.send_raw_email(
                Source=_from_email(),
                Destinations=[to_addr],
                RawMessage={'Data': raw},
            )
            message_id = str(response.get('MessageId') or '')
            results.append({
                'key': key,
                'ok': True,
                'provider_message_id': message_id[:100],
            })
        except Exception as exc:
            logger.exception('SES send failed for %s', key)
            results.append({'key': key, 'ok': False, 'error': str(exc)[:500]})
    return results


def _build_raw_message(*, to_addr: str, subject: str, text: str, html: str) -> bytes:
    if html:
        msg = MIMEMultipart('alternative')
        msg.attach(MIMEText(text or '', 'plain', 'utf-8'))
        msg.attach(MIMEText(html, 'html', 'utf-8'))
    else:
        msg = MIMEText(text or '', 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = _from_email()
    msg['To'] = to_addr
    return msg.as_bytes()
