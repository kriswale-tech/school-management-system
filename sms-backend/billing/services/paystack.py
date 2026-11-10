from __future__ import annotations

import hashlib
import hmac
import uuid
from decimal import Decimal

import requests
from django.conf import settings
from rest_framework.exceptions import ValidationError


PAYSTACK_BASE_URL = 'https://api.paystack.co'


def _secret_key() -> str:
    key = (getattr(settings, 'PAYSTACK_SAAS_SECRET_KEY', None) or '').strip()
    if not key:
        raise ValidationError({'detail': 'Paystack SaaS is not configured.'})
    return key


def _headers() -> dict:
    return {
        'Authorization': f'Bearer {_secret_key()}',
        'Content-Type': 'application/json',
    }


def to_pesewas(amount_ghs: Decimal) -> int:
    return int((Decimal(amount_ghs).quantize(Decimal('0.01')) * 100).to_integral_value())


def from_pesewas(amount_pesewas: int | float | str) -> Decimal:
    return (Decimal(str(amount_pesewas)) / Decimal('100')).quantize(Decimal('0.01'))


def make_reference(prefix: str = 'saas') -> str:
    return f'{prefix}_{uuid.uuid4().hex[:24]}'


def initialize_transaction(
    *,
    email: str,
    amount_ghs: Decimal,
    reference: str,
    callback_url: str,
    metadata: dict | None = None,
) -> dict:
    payload = {
        'email': email or 'billing@schoolasst.local',
        'amount': to_pesewas(amount_ghs),
        'currency': 'GHS',
        'reference': reference,
        'callback_url': callback_url,
        'metadata': metadata or {},
    }
    response = requests.post(
        f'{PAYSTACK_BASE_URL}/transaction/initialize',
        json=payload,
        headers=_headers(),
        timeout=30,
    )
    try:
        body = response.json()
    except ValueError as exc:
        raise ValidationError({'detail': 'Invalid Paystack response.'}) from exc
    if response.status_code >= 400 or not body.get('status'):
        message = body.get('message') or 'Paystack initialize failed.'
        raise ValidationError({'detail': message})
    data = body.get('data') or {}
    return {
        'authorization_url': data.get('authorization_url') or '',
        'access_code': data.get('access_code') or '',
        'reference': data.get('reference') or reference,
        'raw': body,
    }


def verify_transaction(reference: str) -> dict:
    response = requests.get(
        f'{PAYSTACK_BASE_URL}/transaction/verify/{reference}',
        headers=_headers(),
        timeout=30,
    )
    try:
        body = response.json()
    except ValueError as exc:
        raise ValidationError({'detail': 'Invalid Paystack verify response.'}) from exc
    if response.status_code >= 400 or not body.get('status'):
        message = body.get('message') or 'Paystack verify failed.'
        raise ValidationError({'detail': message})
    return body.get('data') or {}


def verify_webhook_signature(*, body: bytes, signature: str) -> bool:
    secret = (
        (getattr(settings, 'PAYSTACK_SAAS_WEBHOOK_SECRET', None) or '').strip()
        or _secret_key()
    )
    digest = hmac.new(secret.encode('utf-8'), body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(digest, signature or '')
