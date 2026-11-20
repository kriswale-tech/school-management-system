"""Amazon SES usage snapshots.

Without AWS credentials, ``sync_ses_usage`` records a placeholder so Platform
Admin can still exercise the Providers UI. With credentials, daily figures
come from the SES send quota and the monthly send total comes from CloudWatch.
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


def _boto_client(service: str):
    import boto3

    return boto3.client(
        service,
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def _metric_period(start, end) -> int:
    """One bucket for a short window, otherwise daily buckets for the month."""
    span = max(int((end - start).total_seconds()), 60)
    if span >= 86400:
        return 86400
    return max(60, (span // 60) * 60)


def fetch_ses_usage() -> dict:
    """SES 24-hour quota plus this month's CloudWatch Send total.

    ``received`` is inbound mail. A send-only identity reports 0.
    SES has no monthly cap, so the monthly limit stays unset.
    """
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    quota = _boto_client('ses').get_send_quota()
    metrics = _boto_client('cloudwatch').get_metric_statistics(
        Namespace='AWS/SES',
        MetricName='Send',
        StartTime=month_start,
        EndTime=now,
        Period=_metric_period(month_start, now),
        Statistics=['Sum'],
    )
    sent = int(round(sum(
        float(point.get('Sum') or 0) for point in metrics.get('Datapoints') or []
    )))
    daily_used = int(round(float(quota.get('SentLast24Hours') or 0)))
    daily_limit = int(round(float(quota.get('Max24HourSend') or 0)))
    return {
        'object': 'ses_usage',
        'configured': True,
        'region': getattr(settings, 'AWS_REGION', '') or None,
        'note': (
            'Daily figures are the SES rolling 24-hour quota. '
            'Monthly sent is the CloudWatch Send total for this month. '
            'Received is inbound mail and stays 0 while the identity only sends.'
        ),
        'emails': {
            'monthly': {'used': sent, 'limit': None, 'sent': sent, 'received': 0},
            'daily': {
                'used': daily_used,
                'limit': daily_limit,
                'sent': daily_used,
                'received': 0,
            },
        },
        'quota': {
            'max_24_hour_send': daily_limit,
            'sent_last_24_hours': daily_used,
            'max_send_rate': quota.get('MaxSendRate'),
        },
    }


def fetch_ses_usage_placeholder() -> dict:
    """Structured placeholder when AWS credentials are not configured."""
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


def send_ses_test_email(*, to: str, subject: str, body: str) -> dict:
    """Send one plain test message through the same SES path as the app."""
    from notifications.services.email_batch import send_email_batch, ses_configured

    if not ses_configured():
        return {'ok': False, 'error': 'SES credentials are not configured on the server.'}
    results = send_email_batch([{
        'key': 'platform-ses-test',
        'to': to,
        'subject': subject,
        'text': body,
    }])
    row = results[0] if results else {'ok': False, 'error': 'SES returned no result.'}
    return {
        'ok': bool(row.get('ok')),
        'error': row.get('error') or '',
        'provider_message_id': row.get('provider_message_id') or '',
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

        payload = fetch_ses_usage()
        parsed = parse_usage_payload(payload)
        snapshot = ResendUsageSnapshot.objects.create(
            provider_account=account,
            raw_response=payload,
            captured_at=timezone.now(),
            source=ResendUsageSnapshot.Source.API,
            captured_by=platform_actor(actor),
            **parsed,
        )
        mark_sync_success(account, metadata={'ses_usage_mode': 'live'})
        return {'ok': True, 'placeholder': False, 'error': '', 'snapshot': snapshot}
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
