"""Versioned messaging pricing configuration (v4.1 §2.6.2–§2.6.3).

Unit prices here are economics / P&L reference values only — nothing is billed
in GHS at send time. Config rows are versioned: an edit deactivates the old row
and creates a new one so historical delivery snapshots stay truthful.
"""

from decimal import Decimal

from django.db import models

from shared.models import BaseModel

# Hardcoded fallbacks (3GPP TS 23.038) used when no config row exists.
DEFAULT_LIMITS = {
    'gsm7': {'single': 160, 'multipart': 153},
    'ucs2': {'single': 70, 'multipart': 67},
}


class SmsEncodingConfig(BaseModel):
    """Segment limits plus provider cost and reference sell price per encoding."""

    class Encoding(models.TextChoices):
        GSM7 = 'gsm7', 'GSM-7'
        UCS2 = 'ucs2', 'UCS-2'

    encoding = models.CharField(max_length=20, choices=Encoding.choices)
    provider_cost_per_segment_ghs = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=Decimal('0.000000'),
        help_text='What the provider charges us per billable segment.',
    )
    school_price_per_segment_ghs = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=Decimal('0.000000'),
        help_text='Reference unit economics only — never charged at send time.',
    )
    single_segment_limit = models.PositiveSmallIntegerField(default=160)
    multipart_segment_limit = models.PositiveSmallIntegerField(default=153)
    effective_from = models.DateTimeField()
    effective_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    changed_by = models.ForeignKey(
        'platform_admin.PlatformUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sms_encoding_configs',
    )
    notes = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['encoding', '-effective_from']
        constraints = [
            models.UniqueConstraint(
                fields=['encoding'],
                condition=models.Q(is_active=True),
                name='uniq_active_sms_encoding_config',
            ),
        ]
        indexes = [
            models.Index(fields=['encoding', 'is_active']),
            models.Index(fields=['encoding', '-effective_from']),
        ]

    def __str__(self):
        return f'{self.encoding} {self.single_segment_limit}/{self.multipart_segment_limit}'

    @property
    def limits(self) -> dict:
        return {
            'single': int(self.single_segment_limit),
            'multipart': int(self.multipart_segment_limit),
        }


class EmailPricingConfig(BaseModel):
    """Email credit economics. Billing unit is locked by v4 to one accepted recipient."""

    BILLING_UNIT = 'accepted_recipient_delivery_attempt'

    school_price_per_credit_ghs = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=Decimal('0.000000'),
        help_text='Reference unit economics only — never charged at send time.',
    )
    estimated_provider_cost_per_email_ghs = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=Decimal('0.000000'),
        help_text='Estimated allocation — Resend bills subscription + overage, not per email.',
    )
    billing_unit = models.CharField(
        max_length=60,
        default=BILLING_UNIT,
        editable=False,
        help_text='Fixed by v4: 1 credit = 1 provider-accepted recipient delivery attempt.',
    )
    effective_from = models.DateTimeField()
    effective_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    changed_by = models.ForeignKey(
        'platform_admin.PlatformUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_pricing_configs',
    )
    notes = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-effective_from']
        constraints = [
            models.UniqueConstraint(
                fields=['is_active'],
                condition=models.Q(is_active=True),
                name='uniq_active_email_pricing_config',
            ),
        ]
        indexes = [
            models.Index(fields=['-effective_from']),
        ]

    def __str__(self):
        return f'email @ {self.school_price_per_credit_ghs} GHS/credit'
