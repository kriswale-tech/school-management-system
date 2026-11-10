"""Amazon SES usage snapshots (placeholder-friendly).

Until AWS credentials exist, ``sync_ses_usage`` records a **placeholder**
snapshot so Platform Admin can exercise the Providers UI end-to-end.
When credentials are present, this still stores a structured snapshot; live
CloudWatch wiring can replace the placeholder payload later without changing
the Messages UI contract.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.utils import timezone

from communications.models import Provider, ProviderChannel, ResendUsageSnapshot
from communications.services.providers.accounts import (
    get_provider_account,
    mark_sync_failure,
    mark_sync_success,
    platform_actor,
)

logger = logging.getLogger(__name__)


def _ses_account():
    return get_provider_account(provider=Provider.SES, channel=ProviderChannel.EMAIL)


def ses_credentials_configured() -> bool:
    return bool(
        getattr(settings, 'EMAIL_ENABLED', False)
        and (getattr(settings, 'EMAIL_PROVIDER', 'ses') or '').lower() == 'ses'
        and (getattr(settings, 'AWS_ACCESS_KEY_ID', '') or '').strip()
        and (getattr(settings, 'AWS_SECRET_ACCESS_KEY', '') or '').strip()
        and (getattr(settings, 'AWS_REGION', '') or '').strip()
    )


def fetch_ses_usage_placeholder() -> dict:
    """Structured placeholder until CloudWatch/Cost Explorer is wired."""
    return {
        'object': 'ses_usage_placeholder',
        'configured': ses_credentials_configured(),
        'region': getattr(settings, 'AWS_REGION', '') or None,
        'note': (
            'Amazon SES usage/cost sync is in placeholder mode. '
            'Add AWS credentials to enable live metrics later.'
        ),
        'emails': {
            'monthly': {'used': None, 'limit': None, 'sent': None, 'received': None},
            'daily': {'used': None, 'limit': None, 'sent': None, 'received': None},
        },
    }


def parse_usage_payload(payload: dict) -> dict:
    emails = (payload or {}).get('emails') or {}
    monthly = emails.get('monthly') or {}
    daily = emails.get('daily') or {}

    def _int(value):
        if value is None or value == '':
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    return {
        'monthly_used': _int(monthly.get('used')),
        'monthly_limit': _int(monthly.get('limit')),
        'daily_used': _int(daily.get('used')),
        'daily_limit': _int(daily.get('limit')),
        'sent_count': _int(monthly.get('sent')),
        'received_count': _int(monthly.get('received')),
    }


def sync_ses_usage(*, actor=None) -> dict:
    """Create a usage snapshot. Never raises to the caller."""
    account = _ses_account()
    try:
        if not ses_credentials_configured():
            payload = fetch_ses_usage_placeholder()
            parsed = parse_usage_payload(payload)
            snapshot = ResendUsageSnapshot.objects.create(
                provider_account=account,
                raw_response=payload,
                captured_at=timezone.now(),
                source=ResendUsageSnapshot.Source.MANUAL,
                captured_by=platform_actor(actor),
                **parsed,
            )
            mark_sync_failure(
                account,
                error='AWS credentials not configured — placeholder snapshot recorded.',
                not_configured=True,
            )
            return {
                'ok': True,
                'placeholder': True,
                'error': '',
                'snapshot': snapshot,
            }

        # Credentials present: still snapshot a placeholder shape for now so the
        # UI works before CloudWatch queries are implemented.
        payload = fetch_ses_usage_placeholder()
        payload['configured'] = True
        payload['note'] = (
            'AWS credentials detected. Live CloudWatch metric pull is not wired yet; '
            'this is a structured placeholder snapshot.'
        )
        parsed = parse_usage_payload(payload)
        snapshot = ResendUsageSnapshot.objects.create(
            provider_account=account,
            raw_response=payload,
            captured_at=timezone.now(),
            source=ResendUsageSnapshot.Source.API,
            captured_by=platform_actor(actor),
            **parsed,
        )
        mark_sync_success(account, metadata={'ses_usage_mode': 'placeholder'})
        return {'ok': True, 'placeholder': True, 'error': '', 'snapshot': snapshot}
    except Exception as exc:
        logger.exception('SES usage sync failed')
        mark_sync_failure(account, error=f'{type(exc).__name__}: {exc}')
        return {
            'ok': False,
            'placeholder': False,
            'error': f'{type(exc).__name__}: {exc}'[:500],
            'snapshot': None,
        }


# Back-compat aliases used by older import paths / beat task renames.
sync_resend_usage = sync_ses_usage


def latest_ses_snapshot() -> ResendUsageSnapshot | None:
    return (
        ResendUsageSnapshot.objects.filter(provider_account__provider=Provider.SES)
        .order_by('-captured_at')
        .first()
    )


def latest_resend_snapshot() -> ResendUsageSnapshot | None:
    """Prefer SES; fall back to legacy Resend rows if present."""
    ses = latest_ses_snapshot()
    if ses is not None:
        return ses
    return (
        ResendUsageSnapshot.objects.filter(provider_account__provider=Provider.RESEND)
        .order_by('-captured_at')
        .first()
    )
