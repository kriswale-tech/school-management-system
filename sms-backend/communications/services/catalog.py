from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from communications.models import CommunicationAddonSku


DEFAULT_SKUS = [
    {
        'code': 'sms_monthly_standard',
        'name': 'SMS Standard (monthly)',
        'channel': CommunicationAddonSku.Channel.SMS,
        'interval': CommunicationAddonSku.Interval.MONTHLY,
        'credits_per_period': 1000,
        'price_ghs': Decimal('80.00'),
        'sort_order': 1,
    },
    {
        'code': 'sms_annual_standard',
        'name': 'SMS Standard (annual)',
        'channel': CommunicationAddonSku.Channel.SMS,
        'interval': CommunicationAddonSku.Interval.ANNUAL,
        'credits_per_period': 12000,
        'price_ghs': Decimal('800.00'),
        'sort_order': 1,
    },
    {
        'code': 'email_monthly_standard',
        'name': 'Email Standard (monthly)',
        'channel': CommunicationAddonSku.Channel.EMAIL,
        'interval': CommunicationAddonSku.Interval.MONTHLY,
        'credits_per_period': 2000,
        'price_ghs': Decimal('40.00'),
        'sort_order': 1,
    },
    {
        'code': 'email_annual_standard',
        'name': 'Email Standard (annual)',
        'channel': CommunicationAddonSku.Channel.EMAIL,
        'interval': CommunicationAddonSku.Interval.ANNUAL,
        'credits_per_period': 24000,
        'price_ghs': Decimal('400.00'),
        'sort_order': 1,
    },
]


@transaction.atomic
def seed_default_skus() -> list[CommunicationAddonSku]:
    from billing.models import Plan

    rows = []
    for row in DEFAULT_SKUS:
        sku, _ = CommunicationAddonSku.objects.update_or_create(
            code=row['code'],
            defaults={
                'name': row['name'],
                'channel': row['channel'],
                'interval': row['interval'],
                'credits_per_period': row['credits_per_period'],
                'price_ghs': row['price_ghs'],
                'sort_order': row['sort_order'],
                'is_active': True,
            },
        )
        rows.append(sku)

    # Bootstrap: gate seeded SKUs to every plan so renewals work after seed.
    plans = list(Plan.objects.all())
    if plans:
        for sku in rows:
            sku.available_plans.set(plans)
    return rows


def default_sku_for(
    *,
    channel: str,
    interval: str,
    plan=None,
) -> CommunicationAddonSku | None:
    qs = CommunicationAddonSku.objects.filter(
        channel=channel,
        interval=interval,
        is_active=True,
    )
    if plan is not None:
        qs = qs.filter(available_plans=plan)
    return qs.order_by('sort_order', 'code').first()
