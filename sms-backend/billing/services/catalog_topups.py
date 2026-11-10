from decimal import Decimal

from billing.models import TopUpPackage
from communications.services.pricing import (
    list_price_ghs,
    price_after_discount_ghs,
    sell_unit_price_ghs,
)

DEFAULT_TOPUP_PACKAGES = [
    {
        'code': 'sms-100',
        'name': 'SMS 100',
        'channel': TopUpPackage.Channel.SMS,
        'credits': 100,
        'discount_percent': Decimal('0.00'),
        'sort_order': 1,
    },
    {
        'code': 'sms-500',
        'name': 'SMS 500',
        'channel': TopUpPackage.Channel.SMS,
        'credits': 500,
        'discount_percent': Decimal('10.00'),
        'sort_order': 2,
    },
    {
        'code': 'sms-2000',
        'name': 'SMS 2000',
        'channel': TopUpPackage.Channel.SMS,
        'credits': 2000,
        'discount_percent': Decimal('15.00'),
        'sort_order': 3,
    },
    {
        'code': 'email-500',
        'name': 'Email 500',
        'channel': TopUpPackage.Channel.EMAIL,
        'credits': 500,
        'discount_percent': Decimal('0.00'),
        'sort_order': 1,
    },
    {
        'code': 'email-2000',
        'name': 'Email 2000',
        'channel': TopUpPackage.Channel.EMAIL,
        'credits': 2000,
        'discount_percent': Decimal('10.00'),
        'sort_order': 2,
    },
    {
        'code': 'email-10000',
        'name': 'Email 10000',
        'channel': TopUpPackage.Channel.EMAIL,
        'credits': 10000,
        'discount_percent': Decimal('20.00'),
        'sort_order': 3,
    },
]


def compute_topup_price(*, channel: str, credits: int, discount_percent=0) -> dict:
    """Derive list and final prices from Messages sell unit price."""
    unit = sell_unit_price_ghs(channel)
    list_price = list_price_ghs(channel=channel, credits=credits)
    final_price = price_after_discount_ghs(
        list_price=list_price,
        discount_percent=discount_percent,
    )
    return {
        'unit_price_ghs': unit,
        'list_price_ghs': list_price,
        'price_ghs': final_price,
        'discount_percent': Decimal(str(discount_percent or 0)),
    }


def apply_topup_pricing(package: TopUpPackage) -> TopUpPackage:
    """Set ``price_ghs`` from channel/credits/discount using Messages sell prices."""
    computed = compute_topup_price(
        channel=package.channel,
        credits=package.credits,
        discount_percent=package.discount_percent,
    )
    package.price_ghs = computed['price_ghs']
    return package


def seed_default_topup_packages() -> list[TopUpPackage]:
    packages = []
    for row in DEFAULT_TOPUP_PACKAGES:
        computed = compute_topup_price(
            channel=row['channel'],
            credits=row['credits'],
            discount_percent=row['discount_percent'],
        )
        package, _ = TopUpPackage.objects.update_or_create(
            code=row['code'],
            defaults={
                'name': row['name'],
                'channel': row['channel'],
                'credits': row['credits'],
                'discount_percent': row['discount_percent'],
                'price_ghs': computed['price_ghs'],
                'sort_order': row['sort_order'],
                'is_active': True,
            },
        )
        packages.append(package)
    return packages
