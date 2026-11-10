from django.db import models

from shared.models import BaseModel


class CreditAccount(BaseModel):
    """Cached balance per school + channel. Mutated only via ledger writer."""

    class Channel(models.TextChoices):
        SMS = 'sms', 'SMS'
        EMAIL = 'email', 'Email'

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='credit_accounts',
    )
    channel = models.CharField(max_length=10, choices=Channel.choices)
    balance = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['school_id', 'channel']
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'channel'],
                name='unique_credit_account_per_school_channel',
            ),
        ]

    def __str__(self):
        return f'{self.school_id} {self.channel}={self.balance}'


class CreditLedgerEntry(BaseModel):
    """Append-only credit movements. Balance changes only through this table."""

    class Channel(models.TextChoices):
        SMS = 'sms', 'SMS'
        EMAIL = 'email', 'Email'

    class EntryType(models.TextChoices):
        ALLOCATION_RECURRING = 'allocation_recurring', 'Recurring allocation'
        TOPUP = 'topup', 'Top-up'
        PROMO_GRANT = 'promo_grant', 'Promo grant'
        USAGE_DEBIT = 'usage_debit', 'Usage debit'
        MANUAL_ADJUST = 'manual_adjust', 'Manual adjustment'
        REVERSAL = 'reversal', 'Reversal'

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='credit_ledger_entries',
    )
    channel = models.CharField(max_length=10, choices=Channel.choices)
    entry_type = models.CharField(max_length=40, choices=EntryType.choices)
    delta = models.IntegerField(help_text='Positive credit, negative debit.')
    balance_after = models.PositiveIntegerField()
    idempotency_key = models.CharField(max_length=191, unique=True)
    occurred_at = models.DateTimeField()
    subscription_period = models.ForeignKey(
        'billing.SubscriptionPeriod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='credit_ledger_entries',
    )
    invoice = models.ForeignKey(
        'billing.Invoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='credit_ledger_entries',
    )
    guardian_delivery = models.ForeignKey(
        'notifications.GuardianDelivery',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='credit_ledger_entries',
    )
    actor_platform_user = models.ForeignKey(
        'platform_admin.PlatformUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='credit_ledger_entries',
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-occurred_at', '-created_at']
        indexes = [
            models.Index(fields=['school', 'channel', '-occurred_at']),
            models.Index(fields=['entry_type', '-occurred_at']),
        ]

    def __str__(self):
        return f'{self.entry_type} {self.delta} ({self.channel})'
