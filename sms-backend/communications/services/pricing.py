"""Messaging pricing configuration: read, version, and snapshot (v4.1 §2.3, §2.6.2).

Versioning discipline: a "change" never mutates a historical row. The active row
is closed (``is_active=False``, ``effective_to=now``) and a new row is appended.
Delivery rows carry snapshots, so re-pricing never rewrites history.
"""

from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from communications.models import DEFAULT_LIMITS, EmailPricingConfig, SmsEncodingConfig
from platform_admin.models import PlatformUser
from platform_admin.services.audit import record_audit

logger = logging.getLogger(__name__)

UNIT_QUANTUM = Decimal('0.000001')
MONEY_QUANTUM = Decimal('0.01')

DEFAULT_SMS_CONFIGS = {
    SmsEncodingConfig.Encoding.GSM7: {
        'single_segment_limit': DEFAULT_LIMITS['gsm7']['single'],
        'multipart_segment_limit': DEFAULT_LIMITS['gsm7']['multipart'],
        'provider_cost_per_segment_ghs': Decimal('0.035000'),
        'school_price_per_segment_ghs': Decimal('0.080000'),
    },
    SmsEncodingConfig.Encoding.UCS2: {
        'single_segment_limit': DEFAULT_LIMITS['ucs2']['single'],
        'multipart_segment_limit': DEFAULT_LIMITS['ucs2']['multipart'],
        'provider_cost_per_segment_ghs': Decimal('0.035000'),
        'school_price_per_segment_ghs': Decimal('0.080000'),
    },
}

DEFAULT_EMAIL_CONFIG = {
    'school_price_per_credit_ghs': Decimal('0.020000'),
    'estimated_provider_cost_per_email_ghs': Decimal('0.004000'),
}


def _platform_actor(actor) -> PlatformUser | None:
    return actor if isinstance(actor, PlatformUser) else None


def to_unit_decimal(value) -> Decimal:
    """Coerce to a 6dp Decimal, treating junk as zero rather than raising."""
    if value is None or value == '':
        return Decimal('0.000000')
    try:
        return Decimal(str(value)).quantize(UNIT_QUANTUM)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0.000000')


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------

def get_active_sms_config(encoding: str) -> SmsEncodingConfig | None:
    return SmsEncodingConfig.objects.filter(encoding=encoding, is_active=True).first()


def get_active_sms_configs() -> dict[str, SmsEncodingConfig]:
    return {
        row.encoding: row
        for row in SmsEncodingConfig.objects.filter(is_active=True)
    }


def get_active_email_config() -> EmailPricingConfig | None:
    return EmailPricingConfig.objects.filter(is_active=True).first()


def money_2(value) -> Decimal:
    """Round to 2dp GHS for catalog / invoice amounts."""
    try:
        return Decimal(str(value)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0.00')


def sell_unit_price_ghs(channel: str) -> Decimal:
    """Active Messages sell price used for catalog list / reference pricing.

    SMS uses the active GSM-7 ``school_price_per_segment_ghs``.
    Email uses the active ``school_price_per_credit_ghs``.
    Falls back to seeded defaults when no config row exists.
    """
    channel = (channel or '').strip().lower()
    if channel == 'sms':
        config = get_active_sms_config(SmsEncodingConfig.Encoding.GSM7)
        if config is not None:
            return to_unit_decimal(config.school_price_per_segment_ghs)
        return to_unit_decimal(
            DEFAULT_SMS_CONFIGS[SmsEncodingConfig.Encoding.GSM7]['school_price_per_segment_ghs'],
        )
    if channel == 'email':
        config = get_active_email_config()
        if config is not None:
            return to_unit_decimal(config.school_price_per_credit_ghs)
        return to_unit_decimal(DEFAULT_EMAIL_CONFIG['school_price_per_credit_ghs'])
    return Decimal('0.000000')


def provider_unit_cost_ghs(channel: str) -> Decimal:
    """Active Messages provider cost per unit (SMS segment / email).

    SMS: GSM-7 ``provider_cost_per_segment_ghs``.
    Email: ``estimated_provider_cost_per_email_ghs``.
    """
    channel = (channel or '').strip().lower()
    if channel == 'sms':
        config = get_active_sms_config(SmsEncodingConfig.Encoding.GSM7)
        if config is not None:
            return to_unit_decimal(config.provider_cost_per_segment_ghs)
        return to_unit_decimal(
            DEFAULT_SMS_CONFIGS[SmsEncodingConfig.Encoding.GSM7]['provider_cost_per_segment_ghs'],
        )
    if channel == 'email':
        config = get_active_email_config()
        if config is not None:
            return to_unit_decimal(config.estimated_provider_cost_per_email_ghs)
        return to_unit_decimal(DEFAULT_EMAIL_CONFIG['estimated_provider_cost_per_email_ghs'])
    return Decimal('0.000000')


def list_price_ghs(*, channel: str, credits: int) -> Decimal:
    """``credits × Messages sell unit price``, rounded to 2dp."""
    units = max(int(credits or 0), 0)
    return money_2(sell_unit_price_ghs(channel) * Decimal(units))


def cost_price_ghs(*, channel: str, credits: int) -> Decimal:
    """``credits × Messages provider unit cost``, rounded to 2dp."""
    units = max(int(credits or 0), 0)
    return money_2(provider_unit_cost_ghs(channel) * Decimal(units))


def price_after_discount_ghs(*, list_price, discount_percent) -> Decimal:
    """Apply a direct percent discount to a list price (clamped 0–100)."""
    try:
        pct = Decimal(str(discount_percent or 0))
    except (InvalidOperation, ValueError, TypeError):
        pct = Decimal('0')
    if pct < 0:
        pct = Decimal('0')
    if pct > 100:
        pct = Decimal('100')
    list_amount = money_2(list_price)
    return money_2(list_amount * (Decimal('100') - pct) / Decimal('100'))


def sms_config_history(encoding: str | None = None):
    qs = SmsEncodingConfig.objects.select_related('changed_by')
    if encoding:
        qs = qs.filter(encoding=encoding)
    return qs.order_by('encoding', '-effective_from', '-created_at')


def email_config_history():
    return EmailPricingConfig.objects.select_related('changed_by').order_by(
        '-effective_from',
        '-created_at',
    )


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------

@transaction.atomic
def ensure_default_sms_configs(*, actor=None) -> list[SmsEncodingConfig]:
    """Create the 3GPP default encoding rows for any encoding with no active row."""
    created: list[SmsEncodingConfig] = []
    now = timezone.now()
    for encoding, defaults in DEFAULT_SMS_CONFIGS.items():
        if SmsEncodingConfig.objects.filter(encoding=encoding, is_active=True).exists():
            continue
        created.append(
            SmsEncodingConfig.objects.create(
                encoding=encoding,
                effective_from=now,
                is_active=True,
                changed_by=_platform_actor(actor),
                notes='Seeded default (3GPP TS 23.038).',
                **defaults,
            ),
        )
    if created:
        invalidate_sms_limit_cache()
    return created


@transaction.atomic
def ensure_default_email_config(*, actor=None) -> EmailPricingConfig | None:
    if EmailPricingConfig.objects.filter(is_active=True).exists():
        return None
    return EmailPricingConfig.objects.create(
        effective_from=timezone.now(),
        is_active=True,
        changed_by=_platform_actor(actor),
        notes='Seeded default.',
        **DEFAULT_EMAIL_CONFIG,
    )


# ---------------------------------------------------------------------------
# Versioned writes
# ---------------------------------------------------------------------------

@transaction.atomic
def create_sms_config_version(
    *,
    encoding: str,
    provider_cost_per_segment_ghs=None,
    school_price_per_segment_ghs=None,
    single_segment_limit: int | None = None,
    multipart_segment_limit: int | None = None,
    notes: str = '',
    actor=None,
    ip_address: str | None = None,
    effective_from=None,
) -> SmsEncodingConfig:
    """Append a new active SMS encoding config version and close the previous one."""
    previous = (
        SmsEncodingConfig.objects.select_for_update()
        .filter(encoding=encoding, is_active=True)
        .first()
    )
    fallback = DEFAULT_SMS_CONFIGS.get(
        encoding,
        DEFAULT_SMS_CONFIGS[SmsEncodingConfig.Encoding.GSM7],
    )
    now = effective_from or timezone.now()

    def _pick(new_value, attr):
        if new_value is not None:
            return new_value
        if previous is not None:
            return getattr(previous, attr)
        return fallback[attr]

    payload = {
        'provider_cost_per_segment_ghs': to_unit_decimal(
            _pick(provider_cost_per_segment_ghs, 'provider_cost_per_segment_ghs'),
        ),
        'school_price_per_segment_ghs': to_unit_decimal(
            _pick(school_price_per_segment_ghs, 'school_price_per_segment_ghs'),
        ),
        'single_segment_limit': int(_pick(single_segment_limit, 'single_segment_limit')),
        'multipart_segment_limit': int(
            _pick(multipart_segment_limit, 'multipart_segment_limit'),
        ),
    }

    if previous is not None:
        # Historical row is closed, never edited in place.
        previous.is_active = False
        previous.effective_to = now
        previous.save(update_fields=['is_active', 'effective_to', 'updated_at'])

    config = SmsEncodingConfig.objects.create(
        encoding=encoding,
        effective_from=now,
        is_active=True,
        changed_by=_platform_actor(actor),
        notes=(notes or '')[:255],
        **payload,
    )
    invalidate_sms_limit_cache()

    record_audit(
        actor=_platform_actor(actor),
        action='messages.sms_pricing.version_created',
        target_type='sms_encoding_config',
        target_id=str(config.pk),
        detail={
            'encoding': encoding,
            'previous_config_id': str(previous.pk) if previous else None,
            'old': _sms_detail(previous),
            'new': _sms_detail(config),
            'notes': notes or '',
        },
        ip_address=ip_address,
    )
    return config


@transaction.atomic
def create_email_config_version(
    *,
    school_price_per_credit_ghs=None,
    estimated_provider_cost_per_email_ghs=None,
    notes: str = '',
    actor=None,
    ip_address: str | None = None,
    effective_from=None,
) -> EmailPricingConfig:
    """Append a new active email pricing version and close the previous one."""
    previous = EmailPricingConfig.objects.select_for_update().filter(is_active=True).first()
    now = effective_from or timezone.now()

    def _pick(new_value, attr):
        if new_value is not None:
            return new_value
        if previous is not None:
            return getattr(previous, attr)
        return DEFAULT_EMAIL_CONFIG[attr]

    payload = {
        'school_price_per_credit_ghs': to_unit_decimal(
            _pick(school_price_per_credit_ghs, 'school_price_per_credit_ghs'),
        ),
        'estimated_provider_cost_per_email_ghs': to_unit_decimal(
            _pick(
                estimated_provider_cost_per_email_ghs,
                'estimated_provider_cost_per_email_ghs',
            ),
        ),
    }

    if previous is not None:
        previous.is_active = False
        previous.effective_to = now
        previous.save(update_fields=['is_active', 'effective_to', 'updated_at'])

    config = EmailPricingConfig.objects.create(
        effective_from=now,
        is_active=True,
        changed_by=_platform_actor(actor),
        notes=(notes or '')[:255],
        **payload,
    )

    record_audit(
        actor=_platform_actor(actor),
        action='messages.email_pricing.version_created',
        target_type='email_pricing_config',
        target_id=str(config.pk),
        detail={
            'previous_config_id': str(previous.pk) if previous else None,
            'old': _email_detail(previous),
            'new': _email_detail(config),
            'notes': notes or '',
        },
        ip_address=ip_address,
    )
    return config


def _sms_detail(config: SmsEncodingConfig | None) -> dict | None:
    if config is None:
        return None
    return {
        'provider_cost_per_segment_ghs': str(config.provider_cost_per_segment_ghs),
        'school_price_per_segment_ghs': str(config.school_price_per_segment_ghs),
        'single_segment_limit': config.single_segment_limit,
        'multipart_segment_limit': config.multipart_segment_limit,
    }


def _email_detail(config: EmailPricingConfig | None) -> dict | None:
    if config is None:
        return None
    return {
        'school_price_per_credit_ghs': str(config.school_price_per_credit_ghs),
        'estimated_provider_cost_per_email_ghs': str(
            config.estimated_provider_cost_per_email_ghs,
        ),
        'billing_unit': config.billing_unit,
    }


# ---------------------------------------------------------------------------
# Snapshots for delivery rows
# ---------------------------------------------------------------------------

def sms_snapshot(*, encoding: str, units: int) -> dict:
    """Cost / price / limit snapshot for one SMS send of ``units`` segments."""
    config = get_active_sms_config(encoding)
    limits = DEFAULT_LIMITS.get(encoding, DEFAULT_LIMITS['gsm7'])
    if config is None:
        return {
            'encoding_snapshot': encoding,
            'segment_limit_snapshot': {
                'single': limits['single'],
                'multipart': limits['multipart'],
                'source': 'default',
            },
            'provider_cost_snapshot_ghs': None,
            'school_unit_price_snapshot_ghs': None,
        }
    quantity = Decimal(max(0, int(units)))
    return {
        'encoding_snapshot': encoding,
        'segment_limit_snapshot': {
            'single': int(config.single_segment_limit),
            'multipart': int(config.multipart_segment_limit),
            'source': 'config',
            'config_id': str(config.pk),
        },
        'provider_cost_snapshot_ghs': (
            config.provider_cost_per_segment_ghs * quantity
        ).quantize(UNIT_QUANTUM),
        'school_unit_price_snapshot_ghs': (
            config.school_price_per_segment_ghs * quantity
        ).quantize(UNIT_QUANTUM),
    }


def email_snapshot(*, units: int = 1) -> dict:
    """Cost / price snapshot for one email send. Provider cost is ESTIMATED."""
    config = get_active_email_config()
    if config is None:
        return {
            'encoding_snapshot': '',
            'segment_limit_snapshot': {},
            'provider_cost_snapshot_ghs': None,
            'school_unit_price_snapshot_ghs': None,
        }
    quantity = Decimal(max(0, int(units)))
    return {
        'encoding_snapshot': '',
        'segment_limit_snapshot': {
            'billing_unit': config.billing_unit,
            'config_id': str(config.pk),
            'provider_cost_is_estimated': True,
        },
        'provider_cost_snapshot_ghs': (
            config.estimated_provider_cost_per_email_ghs * quantity
        ).quantize(UNIT_QUANTUM),
        'school_unit_price_snapshot_ghs': (
            config.school_price_per_credit_ghs * quantity
        ).quantize(UNIT_QUANTUM),
    }


def snapshot_for_channel(*, channel: str, body: str = '', units: int | None = None) -> dict:
    """Snapshot dict ready to splat onto a delivery row for either channel."""
    from communications.services.segments import detect_encoding_key, sms_segment_count

    if channel == 'sms':
        encoding = detect_encoding_key(body or '')
        resolved = units if units is not None else sms_segment_count(body or '')
        return sms_snapshot(encoding=encoding, units=max(1, int(resolved)))
    return email_snapshot(units=max(1, int(units or 1)))


def invalidate_sms_limit_cache() -> None:
    from communications.services.segments import invalidate_limit_cache

    invalidate_limit_cache()
