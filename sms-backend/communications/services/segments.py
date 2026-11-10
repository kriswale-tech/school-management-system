"""SMS segment calculation — config-driven limits, hardcoded safe fallback (v4.1 §2.7).

The algorithm is unchanged from v4 and remains the single source of truth for
school debits: this module is used by the live send path *and* by the platform
calculator endpoint, so the two can never diverge.

Only the segment limits moved from code into ``SmsEncodingConfig``. If no active
config row exists the 3GPP defaults are used, so metering never breaks.
"""

from __future__ import annotations

import logging
import time

from django.db import transaction

logger = logging.getLogger(__name__)

# GSM-7 basic character set (3GPP TS 23.038). Characters outside this force UCS-2.
_GSM7_BASIC = (
    '@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !"#¤%&\'()*+,-./0123456789:;<=>?'
    '¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà'
)
_GSM7_EXTENDED = {'^', '{', '}', '\\', '[', '~', ']', '|', '€'}

ENCODING_GSM7 = 'gsm7'
ENCODING_UCS2 = 'ucs2'

# Display labels kept for backwards compatibility with existing UI payloads.
ENCODING_LABELS = {ENCODING_GSM7: 'GSM-7', ENCODING_UCS2: 'Unicode'}

FALLBACK_LIMITS = {
    ENCODING_GSM7: {'single': 160, 'multipart': 153, 'source': 'default'},
    ENCODING_UCS2: {'single': 70, 'multipart': 67, 'source': 'default'},
}

_LIMIT_CACHE: dict[str, dict] = {}
_LIMIT_CACHE_AT: float = 0.0
_LIMIT_CACHE_TTL_SECONDS = 30.0
_SEED_ATTEMPTED = False


def invalidate_limit_cache() -> None:
    """Drop the in-process limit cache (called whenever a config version lands)."""
    global _LIMIT_CACHE, _LIMIT_CACHE_AT, _SEED_ATTEMPTED
    _LIMIT_CACHE = {}
    _LIMIT_CACHE_AT = 0.0
    _SEED_ATTEMPTED = False


def _maybe_seed_defaults() -> None:
    """Best-effort first-use seeding of the default encoding rows.

    Never raises and never poisons a surrounding transaction: a savepoint wraps
    the write, and any failure just leaves the hardcoded fallback in play.
    """
    global _SEED_ATTEMPTED
    if _SEED_ATTEMPTED:
        return
    _SEED_ATTEMPTED = True
    try:
        from communications.services.pricing import ensure_default_sms_configs

        with transaction.atomic():
            ensure_default_sms_configs()
    except Exception:
        logger.warning('Could not seed default SMS encoding configs', exc_info=True)


def _load_limits() -> dict[str, dict]:
    global _LIMIT_CACHE, _LIMIT_CACHE_AT

    now = time.monotonic()
    if _LIMIT_CACHE and (now - _LIMIT_CACHE_AT) < _LIMIT_CACHE_TTL_SECONDS:
        return _LIMIT_CACHE

    limits = {key: dict(value) for key, value in FALLBACK_LIMITS.items()}
    try:
        from communications.models import SmsEncodingConfig

        rows = list(SmsEncodingConfig.objects.filter(is_active=True))
        if not rows:
            _maybe_seed_defaults()
            rows = list(SmsEncodingConfig.objects.filter(is_active=True))
        for row in rows:
            if row.encoding not in limits:
                continue
            limits[row.encoding] = {
                'single': int(row.single_segment_limit),
                'multipart': int(row.multipart_segment_limit),
                'source': 'config',
                'config_id': str(row.pk),
            }
    except Exception:
        # Database unavailable / pre-migration: stay on the safe defaults.
        logger.debug('Falling back to default SMS segment limits', exc_info=True)

    _LIMIT_CACHE = limits
    _LIMIT_CACHE_AT = now
    return limits


def get_segment_limits(encoding: str) -> dict:
    """Active single/multipart limits for ``encoding`` (``gsm7`` or ``ucs2``)."""
    key = encoding if encoding in FALLBACK_LIMITS else ENCODING_GSM7
    return dict(_load_limits().get(key, FALLBACK_LIMITS[key]))


def _is_gsm7(text: str) -> bool:
    for char in text:
        if char in _GSM7_BASIC or char in _GSM7_EXTENDED:
            continue
        return False
    return True


def _gsm7_septet_length(text: str) -> int:
    length = 0
    for char in text:
        length += 2 if char in _GSM7_EXTENDED else 1
    return length


def detect_encoding_key(message: str) -> str:
    """Return the config key (``gsm7`` / ``ucs2``) for ``message``."""
    return ENCODING_GSM7 if _is_gsm7(message or '') else ENCODING_UCS2


def encoded_length(message: str, encoding: str | None = None) -> int:
    """Septets for GSM-7 (extended chars count 2), UTF-16 code units for UCS-2."""
    text = message or ''
    key = encoding or detect_encoding_key(text)
    if key == ENCODING_GSM7:
        return _gsm7_septet_length(text)
    return len(text)


def segments_for_length(length: int, limits: dict) -> int:
    single = max(1, int(limits.get('single') or 1))
    multipart = max(1, int(limits.get('multipart') or 1))
    if length <= 0:
        return 1
    if length <= single:
        return 1
    return -(-length // multipart)  # ceil division


def sms_segment_count(message: str) -> int:
    """Return provider SMS segments for ``message`` using the active config limits."""
    text = message or ''
    if not text:
        return 1
    key = detect_encoding_key(text)
    return segments_for_length(encoded_length(text, key), get_segment_limits(key))


def sms_encoding(message: str) -> str:
    """Return ``GSM-7`` or ``Unicode`` for credit/segment display."""
    return ENCODING_LABELS[detect_encoding_key(message or '')]


def analyze_sms(message: str) -> dict:
    """Calculator payload. Must match exactly what the live send path debits."""
    text = message or ''
    key = detect_encoding_key(text)
    limits = get_segment_limits(key)
    characters = encoded_length(text, key)
    segments = 1 if not text else segments_for_length(characters, limits)
    return {
        'characters': characters,
        'encoding': ENCODING_LABELS[key],
        'encoding_key': key,
        'segments': segments,
        'credits_per_recipient': segments,
        'limits_used': {
            'single_segment_limit': limits['single'],
            'multipart_segment_limit': limits['multipart'],
            'source': limits.get('source', 'default'),
        },
    }


def units_for_channel(*, channel: str, body: str = '', html_body: str = '') -> int:
    if channel == 'sms':
        return max(1, sms_segment_count(body))
    # Email: one credit per provider-accepted recipient (locked by v4).
    return 1
