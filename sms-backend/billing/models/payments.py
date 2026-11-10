from decimal import Decimal

from django.db import models

from shared.models import BaseModel


class TopUpPackage(BaseModel):
    class Channel(models.TextChoices):
        SMS = 'sms', 'SMS'
        EMAIL = 'email', 'Email'

    code = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=120)
    channel = models.CharField(max_length=10, choices=Channel.choices)
    credits = models.PositiveIntegerField()
    # Charged amount after discount — derived from Messages sell price × credits.
    price_ghs = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Direct package discount applied to list price (credits × Messages sell price).',
    )
    sort_order = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(
        default=False,
        help_text='Inactive until explicitly activated. Schools only see active packages.',
    )

    class Meta:
        ordering = ['channel', 'sort_order', 'credits']

    def __str__(self):
        return f'{self.name} ({self.credits} {self.channel})'


class Payment(BaseModel):
    class Provider(models.TextChoices):
        PAYSTACK = 'paystack', 'Paystack'
        MANUAL = 'manual', 'Manual'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        ABANDONED = 'abandoned', 'Abandoned'

    class Purpose(models.TextChoices):
        INVOICE = 'invoice', 'Invoice payment'
        TOPUP = 'topup', 'Communication top-up'

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='saas_payments',
    )
    invoice = models.ForeignKey(
        'billing.Invoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
    )
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        default=Provider.PAYSTACK,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    amount_ghs = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='GHS')
    reference = models.CharField(max_length=100, unique=True)
    access_code = models.CharField(max_length=100, blank=True, default='')
    authorization_url = models.URLField(blank=True, default='')
    provider_transaction_id = models.CharField(max_length=100, blank=True, default='')
    paid_at = models.DateTimeField(null=True, blank=True)
    raw_initialize = models.JSONField(default=dict, blank=True)
    raw_webhook = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['school', 'status', '-created_at']),
            models.Index(fields=['purpose', 'status']),
        ]

    def __str__(self):
        return f'{self.reference} ({self.status}) {self.amount_ghs} GHS'


class TopUpPurchase(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='topup_purchases',
    )
    package = models.ForeignKey(
        TopUpPackage,
        on_delete=models.PROTECT,
        related_name='purchases',
    )
    invoice = models.OneToOneField(
        'billing.Invoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='topup_purchase',
    )
    payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='topup_purchase',
    )
    channel = models.CharField(max_length=10, choices=TopUpPackage.Channel.choices)
    credits = models.PositiveIntegerField()
    amount_ghs = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    ledger_entry = models.ForeignKey(
        'communications.CreditLedgerEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='topup_purchases',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.channel} +{self.credits} ({self.status})'
