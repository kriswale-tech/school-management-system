from decimal import Decimal

from django.db import models

from shared.models import BaseModel


class Invoice(BaseModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        OPEN = 'open', 'Open'
        PAID = 'paid', 'Paid'
        VOID = 'void', 'Void'
        UNCOLLECTIBLE = 'uncollectible', 'Uncollectible'

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='saas_invoices',
    )
    subscription = models.ForeignKey(
        'billing.SchoolSubscription',
        on_delete=models.CASCADE,
        related_name='invoices',
    )
    currency = models.CharField(max_length=3, default='GHS')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    subtotal_ghs = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    discount_ghs = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_ghs = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    amount_paid_ghs = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    due_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['school', 'status', '-created_at']),
        ]

    def __str__(self):
        return f'Invoice {self.pk} ({self.status}) {self.total_ghs} GHS'


class InvoiceLine(BaseModel):
    class Kind(models.TextChoices):
        APPLICATION = 'application', 'Application subscription'
        APPLICATION_PRORATION = 'application_proration', 'Application upgrade proration'
        INTERVAL_CHANGE = 'interval_change', 'Billing interval change'
        SMS_ADDON = 'sms_addon', 'SMS add-on'
        EMAIL_ADDON = 'email_addon', 'Email add-on'
        TOPUP = 'topup', 'Communication top-up'
        DISCOUNT = 'discount', 'Discount'
        ADJUSTMENT = 'adjustment', 'Adjustment'

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='lines',
    )
    kind = models.CharField(max_length=40, choices=Kind.choices)
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('1.00'))
    unit_price_ghs = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    amount_ghs = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.kind}: {self.amount_ghs} GHS'
