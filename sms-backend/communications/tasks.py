"""Celery tasks for messaging provider sync (v4.1 M2)."""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='communications.sync_arkesel_balance')
def sync_arkesel_balance_task():
    from communications.services.providers import sync_arkesel_balance

    result = sync_arkesel_balance()
    if not result.get('ok'):
        logger.warning('Arkesel balance sync failed: %s', result.get('error'))
    return {
        'ok': bool(result.get('ok')),
        'error': result.get('error') or '',
        'sms_balance': (
            result['snapshot'].sms_balance if result.get('snapshot') is not None else None
        ),
    }


@shared_task(name='communications.sync_ses_usage')
def sync_ses_usage_task():
    from communications.services.providers import sync_ses_usage

    result = sync_ses_usage()
    if not result.get('ok'):
        logger.warning('SES usage sync failed: %s', result.get('error'))
    return {
        'ok': bool(result.get('ok')),
        'placeholder': bool(result.get('placeholder')),
        'error': result.get('error') or '',
        'monthly_used': (
            result['snapshot'].monthly_used if result.get('snapshot') is not None else None
        ),
    }


# Legacy Celery name kept so old beat schedules do not crash mid-deploy.
@shared_task(name='communications.sync_resend_usage')
def sync_resend_usage_task():
    return sync_ses_usage_task()
