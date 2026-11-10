from django.db import models

from shared.models import BaseModel


class SchoolSubscription(BaseModel):
    class Interval(models.TextChoices):
        MONTHLY = 'monthly', 'Monthly'
        ANNUAL = 'annual', 'Annual'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACTIVE = 'active', 'Active'
        PAST_DUE = 'past_due', 'Past due'
        SUSPENDED = 'suspended', 'Suspended'
        CANCELLED = 'cancelled', 'Cancelled'
        EXPIRED = 'expired', 'Expired'

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='subscriptions',
    )
    plan = models.ForeignKey(
        'billing.Plan',
        on_delete=models.PROTECT,
        related_name='subscriptions',
    )
    interval = models.CharField(max_length=20, choices=Interval.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    is_current = models.BooleanField(default=True, db_index=True)
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    grace_period_ends_at = models.DateTimeField(null=True, blank=True)
    dunning_notice_sent_at = models.DateTimeField(null=True, blank=True)
    billing_suspended_school = models.BooleanField(
        default=False,
        help_text='True when dunning suspended the school lifecycle for non-payment.',
    )

    # Communication add-ons (Phase 3)
    sms_addon_enabled = models.BooleanField(default=False)
    email_addon_enabled = models.BooleanField(default=False)
    sms_sku = models.ForeignKey(
        'communications.CommunicationAddonSku',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sms_subscriptions',
    )
    email_sku = models.ForeignKey(
        'communications.CommunicationAddonSku',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_subscriptions',
    )

    pending_plan = models.ForeignKey(
        'billing.Plan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pending_subscriptions',
    )
    pending_interval = models.CharField(
        max_length=20,
        choices=Interval.choices,
        blank=True,
        default='',
    )
    pending_sms_enabled = models.BooleanField(null=True, blank=True)
    pending_email_enabled = models.BooleanField(null=True, blank=True)
    pending_sms_sku = models.ForeignKey(
        'communications.CommunicationAddonSku',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pending_sms_subscriptions',
    )
    pending_email_sku = models.ForeignKey(
        'communications.CommunicationAddonSku',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pending_email_subscriptions',
    )
    pending_change_effective_at = models.DateTimeField(null=True, blank=True)

    # Snapshots for the current period (display / audit)
    plan_code_snapshot = models.CharField(max_length=40, blank=True, default='')
    capacity_max_snapshot = models.PositiveIntegerField(null=True, blank=True)
    staff_capacity_max_snapshot = models.PositiveIntegerField(null=True, blank=True)
    app_price_snapshot_ghs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['school'],
                condition=models.Q(is_current=True),
                name='unique_current_subscription_per_school',
            ),
        ]
        indexes = [
            models.Index(fields=['school', 'status']),
            models.Index(fields=['current_period_end']),
        ]

    def __str__(self):
        return f'{self.school_id} → {self.plan_id} ({self.status})'


class SubscriptionPeriod(BaseModel):
    subscription = models.ForeignKey(
        SchoolSubscription,
        on_delete=models.CASCADE,
        related_name='periods',
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    plan = models.ForeignKey(
        'billing.Plan',
        on_delete=models.PROTECT,
        related_name='periods',
    )
    interval = models.CharField(max_length=20, choices=SchoolSubscription.Interval.choices)
    invoice = models.OneToOneField(
        'billing.Invoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subscription_period',
    )

    class Meta:
        ordering = ['-starts_at']

    def __str__(self):
        return f'Period {self.starts_at.date()}–{self.ends_at.date()} ({self.subscription_id})'
