"""Provider reconciliation jobs and resolution (v4.1 §2.13).

The non-negotiable rule: reconciliation NEVER silently modifies a historical
ledger entry or balance. Resolving an item may APPEND a new typed, idempotent
``manual_adjust`` / ``reversal`` entry that references the item in metadata,
performed by a named actor and written to PlatformAuditLog. Original rows stay
exactly as they were.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from communications.models import (
    CreditLedgerEntry,
    Provider,
    ProviderChannel,
    ProviderReconciliationItem,
    ProviderReconciliationRun,
)
from communications.services.aggregates import provider_accepted_statuses
from communications.services.ledger import manual_adjust, reverse_usage
from platform_admin.models import PlatformUser
from platform_admin.services.audit import record_audit

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_HOURS = 24
MAX_PROVIDER_LOOKUPS = 200


def _platform_actor(actor) -> PlatformUser | None:
    return actor if isinstance(actor, PlatformUser) else None


def _open_item(
    *,
    run: ProviderReconciliationRun,
    delivery=None,
    discrepancy_type: str,
    internal_value: str = '',
    provider_value: str = '',
    provider_payload: dict | None = None,
    detail: str = '',
    delivery_type: str | None = None,
) -> ProviderReconciliationItem:
    return ProviderReconciliationItem.objects.create(
        run=run,
        provider=run.provider,
        channel=run.channel,
        school=getattr(delivery, 'school', None),
        internal_delivery_type=(
            delivery_type or ProviderReconciliationItem.DeliveryType.GUARDIAN
        ),
        internal_delivery_id=str(delivery.pk) if delivery is not None else '',
        provider_message_id=getattr(delivery, 'provider_message_id', '') or '',
        discrepancy_type=discrepancy_type,
        internal_value=str(internal_value)[:120],
        provider_value=str(provider_value)[:120],
        provider_payload=provider_payload or {},
        detail=detail,
    )


def _finish(run: ProviderReconciliationRun, *, error: str = '') -> ProviderReconciliationRun:
    run.status = (
        ProviderReconciliationRun.Status.FAILED
        if error
        else ProviderReconciliationRun.Status.COMPLETED
    )
    run.error_detail = error[:2000]
    run.finished_at = timezone.now()
    run.discrepancy_count = run.items.count()
    run.save(
        update_fields=[
            'status',
            'error_detail',
            'finished_at',
            'discrepancy_count',
            'matched_count',
            'unmatched_count',
            'checked_count',
            'updated_at',
        ],
    )
    return run


def _sweep_unbilled(run: ProviderReconciliationRun) -> int:
    """Surface accepted-but-undebited sends in the window as reconciliation items."""
    from notifications.models import GuardianDelivery

    existing = set(
        ProviderReconciliationItem.objects.filter(
            discrepancy_type=ProviderReconciliationItem.DiscrepancyType.UNBILLED_SEND,
        ).values_list('internal_delivery_id', flat=True),
    )
    count = 0
    unbilled = GuardianDelivery.objects.filter(
        channel=run.channel,
        unbilled=True,
        created_at__gte=run.window_start,
        created_at__lte=run.window_end,
    ).select_related('school')
    for delivery in unbilled:
        if str(delivery.pk) in existing:
            continue
        _open_item(
            run=run,
            delivery=delivery,
            discrepancy_type=ProviderReconciliationItem.DiscrepancyType.UNBILLED_SEND,
            internal_value=str(delivery.segments or 1),
            provider_value='0',
            detail=(
                'Accepted by the provider with no school debit. Requires an '
                'explicit Finance decision; no automatic charge is applied.'
            ),
        )
        count += 1
    return count


def reconcile_arkesel(
    *,
    window_start,
    window_end,
    actor=None,
    limit: int = MAX_PROVIDER_LOOKUPS,
) -> ProviderReconciliationRun:
    """Compare internal SMS submissions with Arkesel's status lookup."""
    from notifications.models import GuardianDelivery
    from notifications.services.sms_status import map_provider_status
    from shared.services.arkesel_sms import extract_status_from_lookup, get_sms_status

    run = ProviderReconciliationRun.objects.create(
        provider=Provider.ARKESEL,
        channel=ProviderChannel.SMS,
        window_start=window_start,
        window_end=window_end,
        started_at=timezone.now(),
        triggered_by=_platform_actor(actor),
    )

    error = ''
    try:
        internal = list(
            GuardianDelivery.objects.filter(
                channel=GuardianDelivery.Channel.SMS,
                created_at__gte=window_start,
                created_at__lte=window_end,
            )
            .select_related('school')
            .order_by('-created_at')[:limit],
        )

        matched = 0
        unmatched = 0
        for delivery in internal:
            run.checked_count += 1
            if not delivery.provider_message_id:
                if delivery.status in provider_accepted_statuses():
                    unmatched += 1
                    _open_item(
                        run=run,
                        delivery=delivery,
                        discrepancy_type=(
                            ProviderReconciliationItem.DiscrepancyType.MISSING_AT_PROVIDER
                        ),
                        internal_value=delivery.status,
                        detail='Accepted internally but carries no provider message id.',
                    )
                continue

            try:
                payload = get_sms_status(delivery.provider_message_id)
            except Exception as exc:
                unmatched += 1
                _open_item(
                    run=run,
                    delivery=delivery,
                    discrepancy_type=(
                        ProviderReconciliationItem.DiscrepancyType.MISSING_AT_PROVIDER
                    ),
                    internal_value=delivery.status,
                    provider_payload={'error': f'{type(exc).__name__}: {exc}'[:300]},
                    detail='Provider status lookup failed for this message id.',
                )
                continue

            raw_status = extract_status_from_lookup(payload)
            mapped = map_provider_status(raw_status)
            if not raw_status:
                unmatched += 1
                _open_item(
                    run=run,
                    delivery=delivery,
                    discrepancy_type=(
                        ProviderReconciliationItem.DiscrepancyType.MISSING_AT_PROVIDER
                    ),
                    internal_value=delivery.status,
                    provider_payload=payload if isinstance(payload, dict) else {},
                    detail='Provider returned no status for this message id.',
                )
                continue

            reported_units = _reported_units(payload)
            if reported_units is not None and reported_units != (delivery.segments or 0):
                _open_item(
                    run=run,
                    delivery=delivery,
                    discrepancy_type=(
                        ProviderReconciliationItem.DiscrepancyType.UNIT_COUNT_MISMATCH
                    ),
                    internal_value=str(delivery.segments or 0),
                    provider_value=str(reported_units),
                    provider_payload=payload if isinstance(payload, dict) else {},
                    detail=(
                        'Provider-reported units differ from the local segment '
                        'count. Flagged for Finance — the ledger is NOT rewritten.'
                    ),
                )
            if reported_units is not None and delivery.provider_units_reported != reported_units:
                delivery.provider_units_reported = reported_units
                delivery.save(update_fields=['provider_units_reported', 'updated_at'])

            if mapped is not None and mapped != delivery.status:
                unmatched += 1
                _open_item(
                    run=run,
                    delivery=delivery,
                    discrepancy_type=(
                        ProviderReconciliationItem.DiscrepancyType.STATUS_MISMATCH
                    ),
                    internal_value=delivery.status,
                    provider_value=raw_status,
                    provider_payload=payload if isinstance(payload, dict) else {},
                    detail='Internal status differs from the provider status.',
                )
            else:
                matched += 1

        run.matched_count = matched
        run.unmatched_count = unmatched
        _sweep_unbilled(run)
    except Exception as exc:
        logger.exception('Arkesel reconciliation failed')
        error = f'{type(exc).__name__}: {exc}'

    run = _finish(run, error=error)
    record_audit(
        actor=_platform_actor(actor),
        action='messages.reconciliation.arkesel_run',
        target_type='provider_reconciliation_run',
        target_id=str(run.pk),
        detail={
            'window_start': window_start.isoformat(),
            'window_end': window_end.isoformat(),
            'checked': run.checked_count,
            'matched': run.matched_count,
            'unmatched': run.unmatched_count,
            'discrepancies': run.discrepancy_count,
            'status': run.status,
        },
    )
    return run


def _reported_units(payload) -> int | None:
    """Pull a provider-reported credit/segment count out of a status payload."""
    if not isinstance(payload, dict):
        return None
    candidates = [payload]
    data = payload.get('data')
    if isinstance(data, dict):
        candidates.append(data)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        candidates.append(data[0])
    for source in candidates:
        for key in ('credits', 'credit_used', 'segments', 'sms_count', 'message_count'):
            value = source.get(key)
            if isinstance(value, bool) or value is None:
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    return None


def reconcile_ses(
    *,
    window_start,
    window_end,
    actor=None,
    stale_after_minutes: int = 60,
) -> ProviderReconciliationRun:
    """Flag guardian emails whose SES delivery status never advanced.

    Comparison is between internal rows and webhook events we received
    (SNS → ``/webhooks/ses/``, stored in ``ResendWebhookEvent`` for now).
    """
    from notifications.models import GuardianDelivery, ResendWebhookEvent

    run = ProviderReconciliationRun.objects.create(
        provider=Provider.SES,
        channel=ProviderChannel.EMAIL,
        window_start=window_start,
        window_end=window_end,
        started_at=timezone.now(),
        triggered_by=_platform_actor(actor),
    )

    error = ''
    try:
        stale_cutoff = timezone.now() - timedelta(minutes=stale_after_minutes)
        internal = list(
            GuardianDelivery.objects.filter(
                channel=GuardianDelivery.Channel.EMAIL,
                created_at__gte=window_start,
                created_at__lte=window_end,
            )
            .select_related('school')
            .order_by('-created_at'),
        )
        run.checked_count = len(internal)

        provider_ids = {
            delivery.provider_message_id
            for delivery in internal
            if delivery.provider_message_id
        }
        seen_events = set(
            ResendWebhookEvent.objects.filter(
                provider_message_id__in=provider_ids,
            ).values_list('provider_message_id', flat=True),
        ) if provider_ids else set()

        matched = 0
        unmatched = 0
        for delivery in internal:
            if not delivery.provider_message_id:
                if delivery.status in provider_accepted_statuses():
                    unmatched += 1
                    _open_item(
                        run=run,
                        delivery=delivery,
                        discrepancy_type=(
                            ProviderReconciliationItem.DiscrepancyType.MISSING_AT_PROVIDER
                        ),
                        internal_value=delivery.status,
                        detail='Accepted internally with no SES message id recorded.',
                    )
                continue

            if delivery.provider_message_id in seen_events:
                matched += 1
                continue

            if (
                delivery.status == GuardianDelivery.Status.SUBMITTED
                and (delivery.status_updated_at or delivery.created_at) <= stale_cutoff
            ):
                unmatched += 1
                _open_item(
                    run=run,
                    delivery=delivery,
                    discrepancy_type=(
                        ProviderReconciliationItem.DiscrepancyType.MISSING_DELIVERY_UPDATE
                    ),
                    internal_value=delivery.status,
                    detail=(
                        'No SES webhook event received for this message id; '
                        'delivery status never advanced past submitted.'
                    ),
                )
            else:
                matched += 1

        orphan_events = ResendWebhookEvent.objects.filter(
            received_at__gte=window_start,
            received_at__lte=window_end,
            matched_delivery_id='',
        ).exclude(provider_message_id='')[:MAX_PROVIDER_LOOKUPS]
        for event in orphan_events:
            unmatched += 1
            ProviderReconciliationItem.objects.create(
                run=run,
                provider=Provider.SES,
                channel=ProviderChannel.EMAIL,
                internal_delivery_type=ProviderReconciliationItem.DeliveryType.NONE,
                provider_message_id=event.provider_message_id,
                discrepancy_type=(
                    ProviderReconciliationItem.DiscrepancyType.MISSING_INTERNALLY
                ),
                provider_value=event.event_type,
                provider_payload=event.payload,
                detail='SES reported a message id with no matching internal record.',
            )

        run.matched_count = matched
        run.unmatched_count = unmatched
        _sweep_unbilled(run)
    except Exception as exc:
        logger.exception('SES reconciliation failed')
        error = f'{type(exc).__name__}: {exc}'

    run = _finish(run, error=error)
    record_audit(
        actor=_platform_actor(actor),
        action='messages.reconciliation.ses_run',
        target_type='provider_reconciliation_run',
        target_id=str(run.pk),
        detail={
            'window_start': window_start.isoformat(),
            'window_end': window_end.isoformat(),
            'checked': run.checked_count,
            'matched': run.matched_count,
            'unmatched': run.unmatched_count,
            'discrepancies': run.discrepancy_count,
            'status': run.status,
        },
    )
    return run


# Legacy name — callers that still say "resend" hit the SES reconciler.
reconcile_resend = reconcile_ses


ADJUSTMENT_KINDS = ('reversal', 'manual_adjust')


@transaction.atomic
def resolve_item(
    *,
    item: ProviderReconciliationItem,
    resolution: str,
    note: str = '',
    actor=None,
    ip_address: str | None = None,
    adjustment: dict | None = None,
) -> ProviderReconciliationItem:
    """Record a resolution, optionally APPENDING a corrective ledger entry.

    ``adjustment`` may be ``{'kind': 'reversal'|'manual_adjust', 'units': int}``.
    Nothing historical is edited; the new entry carries the item id in metadata.
    """
    if resolution not in dict(ProviderReconciliationItem.Resolution.choices):
        raise ValidationError({'resolution': 'Unsupported resolution.'})

    platform_actor = _platform_actor(actor)
    entry: CreditLedgerEntry | None = None

    if adjustment:
        kind = (adjustment.get('kind') or '').strip()
        if kind not in ADJUSTMENT_KINDS:
            raise ValidationError({
                'adjustment': f'kind must be one of: {", ".join(ADJUSTMENT_KINDS)}.',
            })
        if item.school_id is None:
            raise ValidationError({
                'adjustment': 'This item has no school, so no ledger correction applies.',
            })
        units = int(adjustment.get('units') or 0)
        if units == 0:
            raise ValidationError({'adjustment': 'units must be non-zero.'})

        metadata = {
            'reconciliation_item_id': str(item.pk),
            'reconciliation_run_id': str(item.run_id) if item.run_id else None,
            'discrepancy_type': item.discrepancy_type,
            'provider_message_id': item.provider_message_id,
            'note': note or '',
        }
        if kind == 'reversal':
            source_key = adjustment.get('source_idempotency_key') or (
                f'recon:{item.pk}'
            )
            entry = reverse_usage(
                school=item.school,
                channel=item.channel,
                units=abs(units),
                source_idempotency_key=source_key,
                metadata=metadata,
            )
        else:
            entry = manual_adjust(
                school=item.school,
                channel=item.channel,
                delta=units,
                idempotency_key=f'recon-adjust:{item.pk}',
                actor=platform_actor,
                metadata=metadata,
            )
        resolution = ProviderReconciliationItem.Resolution.ADJUSTED

    item.resolution = resolution
    item.resolution_note = note or ''
    item.resolved_by = platform_actor
    item.resolved_at = timezone.now()
    if entry is not None:
        item.ledger_entry = entry
    item.save(
        update_fields=[
            'resolution',
            'resolution_note',
            'resolved_by',
            'resolved_at',
            'ledger_entry',
            'updated_at',
        ],
    )

    record_audit(
        actor=platform_actor,
        action='messages.reconciliation.item_resolved',
        target_type='provider_reconciliation_item',
        target_id=str(item.pk),
        detail={
            'resolution': item.resolution,
            'note': note or '',
            'discrepancy_type': item.discrepancy_type,
            'school_id': str(item.school_id) if item.school_id else None,
            'ledger_entry_id': str(entry.pk) if entry is not None else None,
            'ledger_entry_delta': entry.delta if entry is not None else None,
        },
        ip_address=ip_address,
    )
    return item
