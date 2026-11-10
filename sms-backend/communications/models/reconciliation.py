"""Provider reconciliation records (v4.1 §2.6.6, §2.13).

Hard rule: reconciliation never mutates historical ledger entries. A correction
is a NEW ``manual_adjust`` / ``reversal`` entry that references the item id in
its metadata, performed by a named actor and recorded in PlatformAuditLog.
"""

from django.db import models

from communications.models.providers import Provider, ProviderChannel
from shared.models import BaseModel


class ProviderReconciliationRun(BaseModel):
    class Status(models.TextChoices):
        RUNNING = 'running', 'Running'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    provider = models.CharField(max_length=20, choices=Provider.choices)
    channel = models.CharField(max_length=10, choices=ProviderChannel.choices)
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RUNNING)
    matched_count = models.PositiveIntegerField(default=0)
    unmatched_count = models.PositiveIntegerField(default=0)
    discrepancy_count = models.PositiveIntegerField(default=0)
    checked_count = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    triggered_by = models.ForeignKey(
        'platform_admin.PlatformUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reconciliation_runs',
    )
    error_detail = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['provider', 'channel', '-started_at']),
            models.Index(fields=['status', '-started_at']),
        ]

    def __str__(self):
        return f'{self.provider}/{self.channel} {self.status} @ {self.started_at}'


class ProviderReconciliationItem(BaseModel):
    class DeliveryType(models.TextChoices):
        GUARDIAN = 'guardian_delivery', 'Guardian delivery'
        PLATFORM = 'platform_outbound_delivery', 'Platform outbound delivery'
        NONE = 'none', 'None'

    class DiscrepancyType(models.TextChoices):
        MISSING_INTERNALLY = 'missing_internally', 'Missing internally'
        MISSING_AT_PROVIDER = 'missing_at_provider', 'Missing at provider'
        STATUS_MISMATCH = 'status_mismatch', 'Status mismatch'
        UNIT_COUNT_MISMATCH = 'unit_count_mismatch', 'Unit count mismatch'
        UNBILLED_SEND = 'unbilled_send', 'Unbilled send'
        MISSING_DELIVERY_UPDATE = 'missing_delivery_update', 'Missing delivery update'

    class Resolution(models.TextChoices):
        OPEN = 'open', 'Open'
        ACCEPTED = 'accepted', 'Accepted'
        ADJUSTED = 'adjusted', 'Adjusted'
        IGNORED = 'ignored', 'Ignored'

    run = models.ForeignKey(
        ProviderReconciliationRun,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='items',
        help_text='Null for items raised outside a run (e.g. unbilled-send at send time).',
    )
    provider = models.CharField(max_length=20, choices=Provider.choices)
    channel = models.CharField(max_length=10, choices=ProviderChannel.choices)
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reconciliation_items',
    )
    internal_delivery_type = models.CharField(
        max_length=40,
        choices=DeliveryType.choices,
        default=DeliveryType.GUARDIAN,
    )
    internal_delivery_id = models.CharField(max_length=64, blank=True, default='')
    provider_message_id = models.CharField(max_length=100, blank=True, default='', db_index=True)
    discrepancy_type = models.CharField(max_length=40, choices=DiscrepancyType.choices)
    internal_value = models.CharField(max_length=120, blank=True, default='')
    provider_value = models.CharField(max_length=120, blank=True, default='')
    provider_payload = models.JSONField(default=dict, blank=True)
    detail = models.TextField(blank=True, default='')
    resolution = models.CharField(
        max_length=20,
        choices=Resolution.choices,
        default=Resolution.OPEN,
    )
    resolution_note = models.TextField(blank=True, default='')
    resolved_by = models.ForeignKey(
        'platform_admin.PlatformUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_reconciliation_items',
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    ledger_entry = models.ForeignKey(
        'communications.CreditLedgerEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reconciliation_items',
        help_text='New corrective entry, if one was appended on resolution.',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['run', 'discrepancy_type']),
            models.Index(fields=['resolution', '-created_at']),
            models.Index(fields=['internal_delivery_type', 'internal_delivery_id']),
        ]

    def __str__(self):
        return f'{self.discrepancy_type} ({self.resolution})'
