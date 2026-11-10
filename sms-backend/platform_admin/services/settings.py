from django.db import transaction

from platform_admin.models import PlatformSettings

_SETTINGS_CACHE: PlatformSettings | None = None


def get_platform_settings(*, refresh: bool = False) -> PlatformSettings:
    global _SETTINGS_CACHE
    if _SETTINGS_CACHE is not None and not refresh:
        return _SETTINGS_CACHE

    settings_row = PlatformSettings.objects.order_by('created_at').first()
    if settings_row is None:
        with transaction.atomic():
            settings_row = PlatformSettings.objects.order_by('created_at').first()
            if settings_row is None:
                settings_row = PlatformSettings.objects.create()

    _SETTINGS_CACHE = settings_row
    return settings_row


def update_platform_settings(**fields) -> PlatformSettings:
    settings_row = get_platform_settings(refresh=True)
    for key, value in fields.items():
        setattr(settings_row, key, value)
    settings_row.save(update_fields=[*fields.keys(), 'updated_at'])
    return get_platform_settings(refresh=True)


def clear_platform_settings_cache() -> None:
    global _SETTINGS_CACHE
    _SETTINGS_CACHE = None
