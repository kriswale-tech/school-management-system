from __future__ import annotations

from django.db import transaction
from rest_framework.exceptions import ValidationError

from billing.models import InvoiceLine, SchoolSubscription
from billing.services.capacity import current_subscription
from communications.models import CommunicationAddonSku
from communications.services.catalog import default_sku_for
from communications.services.ledger import allocate_recurring
from platform_admin.models import PlatformUser
from platform_admin.services.audit import record_audit


def _platform_actor(actor) -> PlatformUser | None:
    return actor if isinstance(actor, PlatformUser) else None


def validate_sku_for_subscription(
    *,
    sku: CommunicationAddonSku,
    channel: str,
    interval: str,
    plan=None,
) -> None:
    if sku.channel != channel:
        raise ValidationError({'sku': f'SKU channel must be {channel}.'})
    if sku.interval != interval:
        raise ValidationError({'sku': f'SKU interval must match subscription ({interval}).'})
    if not sku.is_active:
        raise ValidationError({'sku': 'SKU is inactive.'})
    if plan is None:
        raise ValidationError({'sku': 'Subscription plan is required to assign an addon SKU.'})
    if not plan.is_active:
        raise ValidationError({'sku': 'Subscription plan is inactive.'})
    if not sku.available_plans.filter(pk=plan.pk).exists():
        raise ValidationError({
            'sku': f'SKU is not available on plan {plan.code}.',
        })


def _refresh_pending_effective_at(subscription: SchoolSubscription) -> None:
    has_pending = bool(
        subscription.pending_plan_id
        or subscription.pending_interval
        or subscription.pending_sms_enabled is not None
        or subscription.pending_email_enabled is not None
    )
    subscription.pending_change_effective_at = (
        subscription.current_period_end if has_pending else None
    )


@transaction.atomic
def schedule_addon_change(
    *,
    school,
    channel: str,
    enabled: bool,
    sku: CommunicationAddonSku | None = None,
    actor=None,
    ip_address: str | None = None,
) -> SchoolSubscription:
    """Queue SMS/email add-on opt-in/out for the next billing period.

    Scheduling the current enabled state clears a pending change for that channel
    (same pattern as plan schedule cancel).
    """
    subscription = current_subscription(school)
    if subscription is None:
        raise ValidationError({'detail': 'School has no current subscription.'})
    if channel not in (
        CommunicationAddonSku.Channel.SMS,
        CommunicationAddonSku.Channel.EMAIL,
    ):
        raise ValidationError({'channel': 'Invalid channel.'})

    currently_enabled = (
        bool(subscription.sms_addon_enabled)
        if channel == CommunicationAddonSku.Channel.SMS
        else bool(subscription.email_addon_enabled)
    )
    clearing = enabled == currently_enabled

    target_interval = subscription.pending_interval or subscription.interval
    target_plan = subscription.pending_plan or subscription.plan
    if clearing:
        sku = None
    elif enabled:
        sku = sku or default_sku_for(
            channel=channel,
            interval=target_interval,
            plan=target_plan,
        )
        if sku is None:
            raise ValidationError({
                'sku': (
                    f'No active {channel} SKU for {target_interval} '
                    f'on plan {getattr(target_plan, "code", "?")}.'
                ),
            })
        validate_sku_for_subscription(
            sku=sku,
            channel=channel,
            interval=target_interval,
            plan=target_plan,
        )
    else:
        sku = None

    if channel == CommunicationAddonSku.Channel.SMS:
        subscription.pending_sms_enabled = None if clearing else enabled
        subscription.pending_sms_sku = None if clearing else sku
    else:
        subscription.pending_email_enabled = None if clearing else enabled
        subscription.pending_email_sku = None if clearing else sku

    _refresh_pending_effective_at(subscription)
    subscription.save(
        update_fields=[
            'pending_sms_enabled',
            'pending_email_enabled',
            'pending_sms_sku',
            'pending_email_sku',
            'pending_change_effective_at',
            'updated_at',
        ],
    )
    record_audit(
        actor=_platform_actor(actor),
        action=(
            'communications.addon.change_cancelled'
            if clearing
            else 'communications.addon.change_scheduled'
        ),
        target_type='school',
        target_id=str(school.pk),
        detail={
            'channel': channel,
            'enabled': None if clearing else enabled,
            'sku_code': sku.code if sku else None,
            'effective_at': (
                subscription.pending_change_effective_at.isoformat()
                if subscription.pending_change_effective_at
                else None
            ),
        },
        ip_address=ip_address,
    )
    return subscription


def apply_pending_addon_changes(subscription: SchoolSubscription) -> SchoolSubscription:
    updates = []
    if subscription.pending_sms_enabled is not None:
        subscription.sms_addon_enabled = bool(subscription.pending_sms_enabled)
        updates.append('sms_addon_enabled')
        if subscription.pending_sms_enabled:
            subscription.sms_sku = subscription.pending_sms_sku
            updates.append('sms_sku')
        else:
            subscription.sms_sku = None
            updates.append('sms_sku')
        subscription.pending_sms_enabled = None
        subscription.pending_sms_sku = None
        updates.extend(['pending_sms_enabled', 'pending_sms_sku'])

    if subscription.pending_email_enabled is not None:
        subscription.email_addon_enabled = bool(subscription.pending_email_enabled)
        updates.append('email_addon_enabled')
        if subscription.pending_email_enabled:
            subscription.email_sku = subscription.pending_email_sku
            updates.append('email_sku')
        else:
            subscription.email_sku = None
            updates.append('email_sku')
        subscription.pending_email_enabled = None
        subscription.pending_email_sku = None
        updates.extend(['pending_email_enabled', 'pending_email_sku'])

    # Remap SKUs when interval/plan changes and addons stay enabled.
    if subscription.sms_addon_enabled:
        current = subscription.sms_sku
        needs_remap = (
            current is None
            or current.interval != subscription.interval
            or not current.is_allowed_for_plan(subscription.plan)
        )
        if needs_remap:
            subscription.sms_sku = default_sku_for(
                channel=CommunicationAddonSku.Channel.SMS,
                interval=subscription.interval,
                plan=subscription.plan,
            )
            updates.append('sms_sku')
    if subscription.email_addon_enabled:
        current = subscription.email_sku
        needs_remap = (
            current is None
            or current.interval != subscription.interval
            or not current.is_allowed_for_plan(subscription.plan)
        )
        if needs_remap:
            subscription.email_sku = default_sku_for(
                channel=CommunicationAddonSku.Channel.EMAIL,
                interval=subscription.interval,
                plan=subscription.plan,
            )
            updates.append('email_sku')

    if updates:
        subscription.save(update_fields=[*dict.fromkeys(updates), 'updated_at'])
    return subscription


def build_addon_invoice_lines(subscription: SchoolSubscription) -> list[dict]:
    lines: list[dict] = []
    if subscription.sms_addon_enabled and subscription.sms_sku_id:
        sku = subscription.sms_sku
        lines.append({
            'kind': InvoiceLine.Kind.SMS_ADDON,
            'description': f'{sku.name} ({sku.credits_per_period} SMS credits)',
            'quantity': '1',
            'unit_price_ghs': str(sku.price_ghs),
            'amount_ghs': str(sku.price_ghs),
            'metadata': {
                'sku_code': sku.code,
                'credits': sku.credits_per_period,
                'channel': 'sms',
            },
        })
    if subscription.email_addon_enabled and subscription.email_sku_id:
        sku = subscription.email_sku
        lines.append({
            'kind': InvoiceLine.Kind.EMAIL_ADDON,
            'description': f'{sku.name} ({sku.credits_per_period} email credits)',
            'quantity': '1',
            'unit_price_ghs': str(sku.price_ghs),
            'amount_ghs': str(sku.price_ghs),
            'metadata': {
                'sku_code': sku.code,
                'credits': sku.credits_per_period,
                'channel': 'email',
            },
        })
    return lines


def allocate_period_addons(*, subscription: SchoolSubscription, period, invoice=None) -> list:
    """Grant recurring credits for enabled add-ons for ``period`` (idempotent)."""
    granted = []
    if subscription.sms_addon_enabled and subscription.sms_sku_id:
        entry = allocate_recurring(
            school=subscription.school,
            channel='sms',
            credits=subscription.sms_sku.credits_per_period,
            period=period,
            invoice=invoice,
            metadata={'sku_code': subscription.sms_sku.code},
        )
        if entry is not None:
            granted.append(entry)
    if subscription.email_addon_enabled and subscription.email_sku_id:
        entry = allocate_recurring(
            school=subscription.school,
            channel='email',
            credits=subscription.email_sku.credits_per_period,
            period=period,
            invoice=invoice,
            metadata={'sku_code': subscription.email_sku.code},
        )
        if entry is not None:
            granted.append(entry)
    return granted
