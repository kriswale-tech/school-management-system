"""Provider accounts, balance/usage snapshots, purchases and expenses (v4.1 §2.6.4).

Layer 1 of the five money layers: provider wallet / plan. Nothing in here is a
school credit and nothing here may be summed with school balances or cash.
"""

from decimal import Decimal

from django.db import models

from shared.models import BaseModel


class Provider(models.TextChoices):
    ARKESEL = 'arkesel', 'Arkesel'
    SES = 'ses', 'Amazon SES'
    # Legacy — kept so historical ProviderAccount / expense rows remain valid.
    RESEND = 'resend', 'Resend (legacy)'


class ProviderChannel(models.TextChoices):
    SMS = 'sms', 'SMS'
    EMAIL = 'email', 'Email'


class ProviderAccount(BaseModel):
    """One messaging provider account per channel, with derived API health."""

    class ApiStatus(models.TextChoices):
        UNKNOWN = 'unknown', 'Unknown'
        OK = 'ok', 'OK'
        ERROR = 'error', 'Error'
        NOT_CONFIGURED = 'not_configured', 'Not configured'

    provider = models.CharField(max_length=20, choices=Provider.choices)
    channel = models.CharField(max_length=10, choices=ProviderChannel.choices)
    display_name = models.CharField(max_length=120)
    api_status = models.CharField(
        max_length=20,
        choices=ApiStatus.choices,
        default=ApiStatus.UNKNOWN,
    )
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=500, blank=True, default='')
    last_webhook_at = models.DateTimeField(null=True, blank=True)
    webhook_signature_failures = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    # Local Arkesel SMS float. Refreshed from balance sync, then reduced as
    # sends are accepted so concurrent schools cannot all pass one stale reading.
    sms_float_units = models.IntegerField(
        null=True,
        blank=True,
        help_text='Units still safe to promise. Null until a balance is recorded.',
    )
    sms_float_reserved = models.PositiveIntegerField(
        default=0,
        help_text='Units promised to an in-flight Arkesel request.',
    )
    sms_float_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When sms_float_units was last set from an Arkesel balance.',
    )
    sms_low_balance_alerted_at = models.DateTimeField(null=True, blank=True)
    sms_hold_alerted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['provider', 'channel']
        constraints = [
            models.UniqueConstraint(
                fields=['provider', 'channel'],
                name='uniq_provider_account_provider_channel',
            ),
        ]

    def __str__(self):
        return f'{self.provider}/{self.channel}'


class ProviderBalanceSnapshot(BaseModel):
    """Append-only Arkesel wallet reading. Never updated in place."""

    class Source(models.TextChoices):
        API = 'api', 'API sync'
        MANUAL = 'manual', 'Manual capture'

    provider_account = models.ForeignKey(
        ProviderAccount,
        on_delete=models.CASCADE,
        related_name='balance_snapshots',
    )
    sms_balance = models.IntegerField(null=True, blank=True)
    main_balance_text = models.CharField(max_length=120, blank=True, default='')
    raw_response = models.JSONField(default=dict, blank=True)
    captured_at = models.DateTimeField()
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.API)
    captured_by = models.ForeignKey(
        'platform_admin.PlatformUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='provider_balance_snapshots',
    )

    class Meta:
        ordering = ['-captured_at']
        indexes = [
            models.Index(fields=['provider_account', '-captured_at']),
        ]

    def __str__(self):
        return f'{self.provider_account_id} balance={self.sms_balance} @ {self.captured_at}'


class ResendUsageSnapshot(BaseModel):
    """Append-only Resend Usage API reading."""

    class Source(models.TextChoices):
        API = 'api', 'API sync'
        MANUAL = 'manual', 'Manual capture'

    provider_account = models.ForeignKey(
        ProviderAccount,
        on_delete=models.CASCADE,
        related_name='usage_snapshots',
    )
    monthly_used = models.IntegerField(null=True, blank=True)
    monthly_limit = models.IntegerField(null=True, blank=True)
    daily_used = models.IntegerField(null=True, blank=True)
    daily_limit = models.IntegerField(null=True, blank=True)
    sent_count = models.IntegerField(null=True, blank=True)
    received_count = models.IntegerField(null=True, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    captured_at = models.DateTimeField()
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.API)
    captured_by = models.ForeignKey(
        'platform_admin.PlatformUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resend_usage_snapshots',
    )

    class Meta:
        ordering = ['-captured_at']
        indexes = [
            models.Index(fields=['provider_account', '-captured_at']),
        ]

    def __str__(self):
        return f'resend usage {self.monthly_used}/{self.monthly_limit} @ {self.captured_at}'


class ProviderPurchase(BaseModel):
    """Prepaid provider wallet top-up (Arkesel). MANUAL — no purchase API exists."""

    provider = models.CharField(max_length=20, choices=Provider.choices, default=Provider.ARKESEL)
    channel = models.CharField(
        max_length=10,
        choices=ProviderChannel.choices,
        default=ProviderChannel.SMS,
    )
    amount_ghs = models.DecimalField(max_digits=12, decimal_places=2)
    credits_or_units = models.PositiveIntegerField()
    effective_cost_per_unit = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=Decimal('0.000000'),
        help_text='Derived and stored: amount_ghs / credits_or_units.',
    )
    provider_reference = models.CharField(max_length=120, blank=True, default='')
    purchased_at = models.DateTimeField()
    payment_method = models.CharField(max_length=60, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    recorded_by = models.ForeignKey(
        'platform_admin.PlatformUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='provider_purchases',
    )

    class Meta:
        ordering = ['-purchased_at', '-created_at']
        indexes = [
            models.Index(fields=['provider', 'channel', '-purchased_at']),
        ]

    def __str__(self):
        return f'{self.provider} +{self.credits_or_units} for {self.amount_ghs} GHS'

    def recompute_effective_cost(self) -> Decimal:
        units = int(self.credits_or_units or 0)
        if units <= 0:
            self.effective_cost_per_unit = Decimal('0.000000')
        else:
            self.effective_cost_per_unit = (
                Decimal(self.amount_ghs) / Decimal(units)
            ).quantize(Decimal('0.000001'))
        return self.effective_cost_per_unit


class ProviderExpense(BaseModel):
    """Non-wallet provider cost — Resend subscription / overage and similar."""

    class ExpenseKind(models.TextChoices):
        SUBSCRIPTION = 'subscription', 'Subscription'
        OVERAGE = 'overage', 'Overage'
        OTHER = 'other', 'Other'

    class Source(models.TextChoices):
        MANUAL = 'manual', 'Manual'
        IMPORT = 'import', 'Import'

    provider = models.CharField(max_length=20, choices=Provider.choices, default=Provider.SES)
    channel = models.CharField(
        max_length=10,
        choices=ProviderChannel.choices,
        default=ProviderChannel.EMAIL,
    )
    expense_kind = models.CharField(max_length=20, choices=ExpenseKind.choices)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    amount_ghs = models.DecimalField(max_digits=12, decimal_places=2)
    units = models.PositiveIntegerField(null=True, blank=True)
    provider_reference = models.CharField(max_length=120, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)
    recorded_by = models.ForeignKey(
        'platform_admin.PlatformUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='provider_expenses',
    )

    class Meta:
        ordering = ['-period_start', '-created_at']
        indexes = [
            models.Index(fields=['provider', 'expense_kind', '-period_start']),
        ]

    def __str__(self):
        return f'{self.provider} {self.expense_kind} {self.amount_ghs} GHS'
