"""Arkesel wallet balance sync (v4.1 §2.9 — the automatable balance hook).

``GET https://sms.arkesel.com/api/v2/clients/balance-details`` with the
``api-key`` header. Every read appends a ``ProviderBalanceSnapshot``; snapshots
are never updated in place. Arkesel has NO programmatic purchase API, so wallet
top-ups are recorded manually as ``ProviderPurchase`` rows.
"""

from __future__ import annotations

import logging
import re

import requests
from django.conf import settings
from django.utils import timezone

from communications.models import (
    Provider,
    ProviderBalanceSnapshot,
    ProviderChannel,
)
from communications.services.providers.accounts import (
    get_provider_account,
    mark_sync_failure,
    mark_sync_success,
    platform_actor,
)

logger = logging.getLogger(__name__)

ARKESEL_BALANCE_URL = 'https://sms.arkesel.com/api/v2/clients/balance-details'
_NUMERIC = re.compile(r'-?\d+(?:[.,]\d+)?')


def _arkesel_account():
    return get_provider_account(provider=Provider.ARKESEL, channel=ProviderChannel.SMS)


def fetch_arkesel_balance(*, timeout: int = 20) -> dict:
    """Raw balance-details payload. Raises ``requests`` errors for the caller."""
    api_key = (getattr(settings, 'ARKESEL_API_KEY', None) or '').strip()
    if not api_key:
        raise RuntimeError('ARKESEL_API_KEY is not configured.')
    response = requests.get(
        ARKESEL_BALANCE_URL,
        headers={'api-key': api_key},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, dict) else {'data': payload}


def _coerce_int(value) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    match = _NUMERIC.search(str(value))
    if match is None:
        return None
    try:
        return int(float(match.group(0).replace(',', '')))
    except (TypeError, ValueError):
        return None


def parse_balance_payload(payload: dict) -> dict:
    """Pull SMS balance and the human-readable main balance out of the payload.

    Arkesel has shipped several shapes for this endpoint, so every candidate key
    is probed and the raw response is always stored alongside the parse.
    """
    data = payload.get('data') if isinstance(payload, dict) else None
    source = data if isinstance(data, dict) else payload
    if isinstance(data, list) and data and isinstance(data[0], dict):
        source = data[0]
    if not isinstance(source, dict):
        source = {}

    sms_balance = None
    for key in ('sms_balance', 'smsBalance', 'balance', 'credit', 'credits', 'units'):
        sms_balance = _coerce_int(source.get(key))
        if sms_balance is not None:
            break

    main_balance_text = ''
    for key in ('main_balance', 'mainBalance', 'main_balance_text', 'wallet_balance'):
        value = source.get(key)
        if value not in (None, ''):
            main_balance_text = str(value)[:120]
            break

    return {'sms_balance': sms_balance, 'main_balance_text': main_balance_text}


def sync_arkesel_balance(*, actor=None) -> dict:
    """Fetch and snapshot the Arkesel balance. Never raises to the caller."""
    account = _arkesel_account()
    try:
        payload = fetch_arkesel_balance()
    except RuntimeError as exc:
        mark_sync_failure(account, error=str(exc), not_configured=True)
        _notify_float_sync_problem(str(exc))
        return {'ok': False, 'error': str(exc), 'snapshot': None}
    except Exception as exc:
        logger.exception('Arkesel balance sync failed')
        error = f'{type(exc).__name__}: {exc}'[:500]
        mark_sync_failure(account, error=error)
        _notify_float_sync_problem(error)
        return {'ok': False, 'error': error, 'snapshot': None}

    parsed = parse_balance_payload(payload)
    snapshot = ProviderBalanceSnapshot.objects.create(
        provider_account=account,
        sms_balance=parsed['sms_balance'],
        main_balance_text=parsed['main_balance_text'],
        raw_response=payload,
        captured_at=timezone.now(),
        source=ProviderBalanceSnapshot.Source.API,
        captured_by=platform_actor(actor),
    )
    mark_sync_success(account, metadata={'last_sms_balance': parsed['sms_balance']})
    _apply_float_reading(account, parsed['sms_balance'], notify_if_missing=True)
    return {'ok': True, 'error': '', 'snapshot': snapshot}


def record_manual_arkesel_balance(
    *,
    sms_balance: int | None,
    main_balance_text: str = '',
    actor=None,
    notes: str = '',
) -> ProviderBalanceSnapshot:
    """Human-entered balance capture when the API is unavailable."""
    account = _arkesel_account()
    snapshot = ProviderBalanceSnapshot.objects.create(
        provider_account=account,
        sms_balance=sms_balance,
        main_balance_text=(main_balance_text or '')[:120],
        raw_response={'source': 'manual', 'notes': notes},
        captured_at=timezone.now(),
        source=ProviderBalanceSnapshot.Source.MANUAL,
        captured_by=platform_actor(actor),
    )
    _apply_float_reading(account, sms_balance)
    return snapshot


def _apply_float_reading(account, sms_balance, *, notify_if_missing: bool = False) -> None:
    if sms_balance is None:
        if notify_if_missing:
            _notify_float_sync_problem(
                'Arkesel balance response did not include an SMS balance.',
            )
        return
    from communications.services.providers.sms_float import apply_synced_balance

    apply_synced_balance(account, int(sms_balance))


def _notify_float_sync_problem(error: str) -> None:
    from communications.services.providers.sms_float import notify_sync_problem

    try:
        notify_sync_problem(error)
    except Exception:
        logger.exception('Could not email platform admins about the Arkesel balance')


def latest_arkesel_snapshot() -> ProviderBalanceSnapshot | None:
    return (
        ProviderBalanceSnapshot.objects.filter(
            provider_account__provider=Provider.ARKESEL,
        )
        .order_by('-captured_at')
        .first()
    )
