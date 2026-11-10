"""ProviderAccount lifecycle and derived API / webhook health (v4.1 §2.8, §2.9)."""

from __future__ import annotations

from django.utils import timezone

from communications.models import Provider, ProviderAccount, ProviderChannel
from platform_admin.models import PlatformUser

ARKESEL_DEFAULTS = {
    'provider': Provider.ARKESEL,
    'channel': ProviderChannel.SMS,
    'display_name': 'Arkesel SMS',
}

SES_DEFAULTS = {
    'provider': Provider.SES,
    'channel': ProviderChannel.EMAIL,
    'display_name': 'Amazon SES',
}


def platform_actor(actor) -> PlatformUser | None:
    return actor if isinstance(actor, PlatformUser) else None


def ensure_provider_accounts() -> list[ProviderAccount]:
    """Idempotently create the Arkesel and Amazon SES account rows."""
    rows = []
    for defaults in (ARKESEL_DEFAULTS, SES_DEFAULTS):
        account, _ = ProviderAccount.objects.get_or_create(
            provider=defaults['provider'],
            channel=defaults['channel'],
            defaults={'display_name': defaults['display_name']},
        )
        rows.append(account)
    return rows


def get_provider_account(*, provider: str, channel: str) -> ProviderAccount:
    display = {
        (Provider.ARKESEL, ProviderChannel.SMS): 'Arkesel SMS',
        (Provider.SES, ProviderChannel.EMAIL): 'Amazon SES',
        (Provider.RESEND, ProviderChannel.EMAIL): 'Resend Email (legacy)',
    }.get((provider, channel), f'{provider} {channel}')
    account, _ = ProviderAccount.objects.get_or_create(
        provider=provider,
        channel=channel,
        defaults={'display_name': display},
    )
    return account


def mark_sync_success(account: ProviderAccount, *, metadata: dict | None = None) -> ProviderAccount:
    account.api_status = ProviderAccount.ApiStatus.OK
    account.last_synced_at = timezone.now()
    account.last_error = ''
    if metadata:
        account.metadata = {**(account.metadata or {}), **metadata}
    account.save(
        update_fields=[
            'api_status',
            'last_synced_at',
            'last_error',
            'metadata',
            'updated_at',
        ],
    )
    return account


def mark_sync_failure(
    account: ProviderAccount,
    *,
    error: str,
    not_configured: bool = False,
) -> ProviderAccount:
    account.api_status = (
        ProviderAccount.ApiStatus.NOT_CONFIGURED
        if not_configured
        else ProviderAccount.ApiStatus.ERROR
    )
    account.last_synced_at = timezone.now()
    account.last_error = (error or '')[:500]
    account.save(
        update_fields=['api_status', 'last_synced_at', 'last_error', 'updated_at'],
    )
    return account


def mark_webhook_received(account: ProviderAccount) -> None:
    account.last_webhook_at = timezone.now()
    account.save(update_fields=['last_webhook_at', 'updated_at'])


def mark_webhook_signature_failure(account: ProviderAccount) -> None:
    ProviderAccount.objects.filter(pk=account.pk).update(
        webhook_signature_failures=(account.webhook_signature_failures or 0) + 1,
        updated_at=timezone.now(),
    )
