"""Free / sponsored messaging allowances (v4.1 §2.6.5, §2.11).

An allowance is NOT a wallet. Consumption is counted from classified delivery
rows in the window — no credits move and no school ledger entry is written.
A promotional *credit* grant stays an ordinary ``promo_grant`` ledger entry.
"""

from django.db import models

from shared.models import BaseModel


class MessagingAllowancePolicy(BaseModel):
    """Platform-configured free or sponsored messaging budget."""

    class Scope(models.TextChoices):
        SCHOOL = 'school', 'Single school'
        PLATFORM = 'platform', 'Platform-wide'

    class Channel(models.TextChoices):
        SMS = 'sms', 'SMS'
        EMAIL = 'email', 'Email'

    class Classification(models.TextChoices):
        FREE = 'free', 'Free allowance'
        SPONSORED = 'sponsored', 'Sponsored campaign'

    class ExhaustedBehavior(models.TextChoices):
        FALLBACK_PAID = 'fallback_paid', 'Fall back to paid credits'
        SKIP = 'skip', 'Skip the send'

    name = models.CharField(max_length=120)
    scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.SCHOOL)
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='messaging_allowance_policies',
    )
    channel = models.CharField(max_length=10, choices=Channel.choices)
    classification = models.CharField(
        max_length=20,
        choices=Classification.choices,
        default=Classification.FREE,
        help_text='Delivery rows covered by this policy are stamped with this classification.',
    )
    monthly_free_units = models.PositiveIntegerField(default=0)
    daily_limit_units = models.PositiveIntegerField(null=True, blank=True)
    applies_to_events = models.JSONField(
        default=list,
        blank=True,
        help_text='GuardianDelivery.EventType values; empty list means all events.',
    )
    budget_ghs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Optional provider-cost spend cap for the policy window.',
    )
    alert_thresholds = models.JSONField(
        default=list,
        blank=True,
        help_text='Fractions of the allowance that raise an alert, e.g. [0.8, 0.95].',
    )
    exhausted_behavior = models.CharField(
        max_length=20,
        choices=ExhaustedBehavior.choices,
        default=ExhaustedBehavior.FALLBACK_PAID,
        help_text='Explicit configured choice — never an implicit surprise charge.',
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(
        'platform_admin.PlatformUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messaging_allowance_policies',
    )

    class Meta:
        ordering = ['-starts_at', 'name']
        indexes = [
            models.Index(fields=['scope', 'channel', 'is_active']),
            models.Index(fields=['school', 'channel', 'is_active']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(scope='platform', school__isnull=True)
                | models.Q(scope='school', school__isnull=False),
                name='allowance_school_matches_scope',
            ),
        ]

    def __str__(self):
        target = self.school_id or 'platform'
        return f'{self.name} ({self.channel} → {target})'

    def covers_event(self, event_type: str) -> bool:
        events = self.applies_to_events or []
        if not events:
            return True
        return event_type in events
