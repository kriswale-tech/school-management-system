"""Refund and unbilled-send policy for post-acceptance outcomes (v4.1 §2.14).

Policy:
    failed after provider acceptance, credits_charged > 0  → one idempotent
                                                             ``reverse_usage``
    provider genuinely charges for failed attempts          → keep the debit
                                                             (settings flag off)
    status unknown                                          → NO auto-refund;
                                                             reconcile first
    accepted but the debit raced to InsufficientCredits     → record an
                                                             ``unbilled_send``
                                                             reconciliation item

Nothing here edits a historical ledger row. Corrections are appended.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction

from communications.models import (
    CreditLedgerEntry,
    Provider,
    ProviderReconciliationItem,
)
from communications.services.ledger import reverse_usage
from platform_admin.services.audit import record_audit

logger = logging.getLogger(__name__)

PROVIDER_BY_CHANNEL = {
    'sms': Provider.ARKESEL,
    'email': Provider.SES,
}


def auto_refund_enabled(channel: str) -> bool:
    """Whether a failed DLR/webhook should auto-reverse the school debit."""
    flag = {
        'sms': 'MESSAGING_AUTO_REFUND_FAILED_SMS',
        'email': 'MESSAGING_AUTO_REFUND_FAILED_EMAIL',
    }.get(channel)
    if flag is None:
        return False
    return bool(getattr(settings, flag, True))


@transaction.atomic
def refund_failed_delivery(delivery, *, source: str = 'provider_status') -> CreditLedgerEntry | None:
    """Reverse the usage debit for a delivery that failed after acceptance.

    Idempotent on ``reversal:usage:{original_key}`` — a duplicate DLR or
    webhook can never produce a second credit. Returns the ledger entry, or
    ``None`` when no refund applies.
    """
    from notifications.models import GuardianDelivery

    if delivery is None:
        return None
    if delivery.billing_classification != GuardianDelivery.BillingClassification.PAID:
        # Free / sponsored sends never debited, so there is nothing to reverse.
        return None
    if delivery.status != GuardianDelivery.Status.FAILED:
        return None
    charged = int(delivery.credits_charged or 0)
    if charged <= 0:
        return None
    if not auto_refund_enabled(delivery.channel):
        logger.info(
            'Auto-refund disabled for %s; keeping debit on delivery=%s',
            delivery.channel,
            delivery.pk,
        )
        return None

    entry = reverse_usage(
        school=delivery.school,
        channel=delivery.channel,
        units=charged,
        source_idempotency_key=f'usage:{delivery.idempotency_key}',
        metadata={
            'reason': 'provider_failed_after_acceptance',
            'source': source,
            'guardian_delivery_id': str(delivery.pk),
            'provider_message_id': delivery.provider_message_id or '',
        },
    )

    already_refunded = int(delivery.credits_refunded or 0)
    if already_refunded < charged:
        delivery.credits_refunded = charged
        delivery.save(update_fields=['credits_refunded', 'updated_at'])

    if entry is not None and entry.guardian_delivery_id is None:
        # Link the appended reversal back to the row it corrects.
        entry.guardian_delivery = delivery
        entry.save(update_fields=['guardian_delivery', 'updated_at'])

    logger.info(
        'Refunded %s %s credit(s) for failed delivery=%s via %s',
        charged,
        delivery.channel,
        delivery.pk,
        source,
    )
    return entry


def record_unbilled_send(*, delivery, school, channel: str, units: int, actor=None):
    """Flag an accepted-but-undebited send instead of silently dropping it.

    The architecture left the debit-after-accept race as an open decision
    (§2.1.2). Implemented choice: keep ``allow_negative=False`` so the wallet
    never goes negative, mark the delivery ``unbilled=True``, raise an
    ``unbilled_send`` reconciliation item, and audit it for Finance.
    """
    item = None
    try:
        with transaction.atomic():
            if delivery is not None and not delivery.unbilled:
                delivery.unbilled = True
                delivery.credits_charged = 0
                delivery.save(
                    update_fields=['unbilled', 'credits_charged', 'updated_at'],
                )
            item, _ = ProviderReconciliationItem.objects.get_or_create(
                internal_delivery_type=(
                    ProviderReconciliationItem.DeliveryType.GUARDIAN
                ),
                internal_delivery_id=str(delivery.pk) if delivery else '',
                discrepancy_type=ProviderReconciliationItem.DiscrepancyType.UNBILLED_SEND,
                defaults={
                    'provider': PROVIDER_BY_CHANNEL.get(channel, Provider.ARKESEL),
                    'channel': channel,
                    'school': school,
                    'provider_message_id': (
                        delivery.provider_message_id if delivery else ''
                    ),
                    'internal_value': str(units),
                    'provider_value': '0',
                    'detail': (
                        'Provider accepted the send but the school credit debit '
                        'failed (insufficient balance between pre-check and debit). '
                        'No credits were taken; requires a Finance decision.'
                    ),
                    'provider_payload': {
                        'idempotency_key': delivery.idempotency_key if delivery else '',
                        'units': units,
                    },
                },
            )
    except Exception:
        logger.exception(
            'Failed to record unbilled send for delivery=%s',
            getattr(delivery, 'pk', None),
        )
        return None

    try:
        record_audit(
            actor=actor,
            action='messages.unbilled_send.recorded',
            target_type='guardian_delivery',
            target_id=str(delivery.pk) if delivery else '',
            detail={
                'school_id': str(school.pk) if school else None,
                'channel': channel,
                'units': units,
                'reconciliation_item_id': str(item.pk) if item else None,
            },
        )
    except Exception:
        logger.exception('Failed to audit unbilled send')
    return item
