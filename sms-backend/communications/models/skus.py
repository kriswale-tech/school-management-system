from decimal import Decimal

from django.db import models

from shared.models import BaseModel


class CommunicationAddonSku(BaseModel):
    """Recurring SMS or email allowance sold on the application billing interval."""

    class Channel(models.TextChoices):
        SMS = 'sms', 'SMS'
        EMAIL = 'email', 'Email'

    class Interval(models.TextChoices):
        MONTHLY = 'monthly', 'Monthly'
        ANNUAL = 'annual', 'Annual'

    code = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=120)
    channel = models.CharField(max_length=10, choices=Channel.choices)
    interval = models.CharField(max_length=20, choices=Interval.choices)
    credits_per_period = models.PositiveIntegerField()
    price_ghs = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    sort_order = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(
        default=False,
        help_text='Inactive until explicitly activated. Schools only see active SKUs.',
    )
    # Empty set = available on no plans (must assign before selling).
    available_plans = models.ManyToManyField(
        'billing.Plan',
        blank=True,
        related_name='communication_addon_skus',
        help_text='Plans that may opt into this SKU.',
    )

    class Meta:
        ordering = ['channel', 'interval', 'sort_order', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['channel', 'interval', 'code'],
                name='unique_comms_sku_channel_interval_code',
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.channel}/{self.interval})'

    def is_allowed_for_plan(self, plan) -> bool:
        if plan is None or not getattr(plan, 'is_active', False):
            return False
        if not self.is_active:
            return False
        return self.available_plans.filter(pk=plan.pk).exists()
