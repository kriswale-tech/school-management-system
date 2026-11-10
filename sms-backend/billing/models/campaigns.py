from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from shared.models import BaseModel


class PromotionCampaign(BaseModel):
    """A platform discount rule. Invoice time decides how much of a period it covers."""

    class AppliesTo(models.TextChoices):
        APPLICATION = 'application', 'Application only'
        COMMUNICATION = 'communication', 'Communication add-ons'
        ALL = 'all', 'Application and communication'

    class Schedule(models.TextChoices):
        INTRODUCTORY = 'introductory', 'First months of the school'
        RECURRING = 'recurring', 'Every invoice'
        DATE_RANGE = 'date_range', 'Date range'

    class Audience(models.TextChoices):
        ALL = 'all', 'All schools'
        NEW = 'new', 'New schools'
        SELECTED = 'selected', 'Selected schools'

    code = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=150)
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('100.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
    )
    applies_to = models.CharField(
        max_length=20,
        choices=AppliesTo.choices,
        default=AppliesTo.APPLICATION,
    )
    schedule = models.CharField(
        max_length=20,
        choices=Schedule.choices,
        default=Schedule.INTRODUCTORY,
    )
    audience = models.CharField(
        max_length=20,
        choices=Audience.choices,
        default=Audience.NEW,
    )
    billing_interval = models.CharField(
        max_length=20,
        blank=True,
        default='',
        help_text='Blank applies on monthly and annual invoices. Otherwise the school must be on this interval.',
    )
    duration_months = models.PositiveSmallIntegerField(
        default=12,
        help_text='Introductory discounts cover this many months from the school subscription start.',
    )
    starts_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Date-range discounts include a billing month that starts on or after this moment.',
    )
    ends_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Date-range discounts stop at this moment. A month that starts here is full price.',
    )
    is_active = models.BooleanField(default=True)
    first_subscription_only = models.BooleanField(
        default=True,
        help_text='Kept in step with audience=new. Only a school\'s first subscription can redeem this.',
    )
    schools = models.ManyToManyField(
        'schools.School',
        blank=True,
        related_name='promotion_campaigns',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.discount_percent}%)'

    def save(self, *args, **kwargs):
        self.first_subscription_only = self.audience == self.Audience.NEW
        super().save(*args, **kwargs)


class PromotionRedemption(BaseModel):
    """Frozen copy of a discount for one school. Later edits to the rule do not rewrite it."""

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='promotion_redemptions',
    )
    campaign = models.ForeignKey(
        PromotionCampaign,
        on_delete=models.PROTECT,
        related_name='redemptions',
    )
    subscription = models.ForeignKey(
        'billing.SchoolSubscription',
        on_delete=models.CASCADE,
        related_name='promotion_redemptions',
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    applies_to = models.CharField(
        max_length=20,
        choices=PromotionCampaign.AppliesTo.choices,
        default=PromotionCampaign.AppliesTo.APPLICATION,
    )
    schedule = models.CharField(
        max_length=20,
        choices=PromotionCampaign.Schedule.choices,
        default=PromotionCampaign.Schedule.INTRODUCTORY,
    )
    billing_interval = models.CharField(max_length=20, blank=True, default='')
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'campaign'],
                name='unique_school_campaign_redemption',
            ),
        ]

    def __str__(self):
        return f'{self.campaign_id} @ {self.school_id}'
