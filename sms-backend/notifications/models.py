from django.db import models

from shared.models import BaseModel


class Notification(BaseModel):
    """Personal in-app notice for one school membership.

    Distinct from schools alerts (live digests) and activities (school history).
    Email delivery is queued via Celery when EMAIL_ENABLED and the user has an email.
    """

    class EventType(models.TextChoices):
        SCORES_PUBLISHED = 'scores_published', 'Scores published'
        STUDENTS_APPROVED = 'students_approved', 'Students approved'
        STUDENT_REJECTED = 'student_rejected', 'Student rejected'
        REOPEN_REQUESTED = 'reopen_requested', 'Reopen requested'
        REPORTS_RELEASED = 'reports_released', 'Reports released'
        CORRECTION_SENT = 'correction_sent', 'Correction sent'
        CORRECTION_APPLIED = 'correction_applied', 'Correction applied'
        REOPEN_DECLINED = 'reopen_declined', 'Reopen declined'
        CLASS_TEACHER_ASSIGNED = 'class_teacher_assigned', 'Class teacher assigned'
        SUBJECT_TEACHER_ASSIGNED = 'subject_teacher_assigned', 'Subject teacher assigned'
        STUDENT_ENROLLED = 'student_enrolled', 'Student enrolled'
        STUDENT_LEFT = 'student_left', 'Student left'
        STUDENT_REACTIVATED = 'student_reactivated', 'Student reactivated'
        STUDENT_UPDATED = 'student_updated', 'Student profile updated'
        GUARDIAN_UPDATED = 'guardian_updated', 'Guardian updated'
        MEMBER_INVITED = 'member_invited', 'Member invited'
        MEMBER_UPDATED = 'member_updated', 'Member profile updated'
        MEMBER_PHONE_CHANGED = 'member_phone_changed', 'Member phone changed'
        MEMBER_ROLE_CHANGED = 'member_role_changed', 'Member role changed'
        TERM_OPENED = 'term_opened', 'Term opened'

    class EmailStatus(models.TextChoices):
        SKIPPED = 'skipped', 'Skipped'
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    recipient = models.ForeignKey(
        'accounts.SchoolMembership',
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    actor = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications_sent',
    )
    event_type = models.CharField(max_length=40, choices=EventType.choices)
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=500)
    href = models.CharField(max_length=500, blank=True)
    target_kind = models.CharField(max_length=40, blank=True)
    target_id = models.UUIDField(null=True, blank=True)
    activity = models.ForeignKey(
        'activities.Activity',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
    )
    read_at = models.DateTimeField(null=True, blank=True)
    email_status = models.CharField(
        max_length=20,
        choices=EmailStatus.choices,
        default=EmailStatus.SKIPPED,
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'read_at']),
            models.Index(fields=['school', 'event_type', '-created_at']),
        ]

    def __str__(self):
        return f'{self.event_type} → {self.recipient_id}'


class BillingClassification(models.TextChoices):
    """How an outbound attempt is funded (v4.1 §2.10).

    ``paid`` debits the school credit ledger. ``free`` and ``sponsored`` never
    debit a school wallet — the platform absorbs the provider cost.
    """

    PAID = 'paid', 'Paid by school credits'
    FREE = 'free', 'Free (platform funded)'
    SPONSORED = 'sponsored', 'Sponsored campaign'


class GuardianDelivery(BaseModel):
    """Outbound SMS/email attempt to a Parent contact (not a staff inbox row)."""

    BillingClassification = BillingClassification

    class EventType(models.TextChoices):
        WARD_ENROLLED = 'ward_enrolled', 'Ward enrolled'
        PAYMENT_RECEIPT = 'payment_receipt', 'Payment receipt'
        DEBT_REMINDER = 'debt_reminder', 'Debt reminder'
        REPORT_READY = 'report_ready', 'Report ready'
        NEXT_TERM_FEES = 'next_term_fees', 'Next term fees'

    class Channel(models.TextChoices):
        SMS = 'sms', 'SMS'
        EMAIL = 'email', 'Email'

    class Status(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        PROCESSING = 'processing', 'Processing'
        SUBMITTED = 'submitted', 'Submitted'
        DELIVERED = 'delivered', 'Delivered'
        FAILED = 'failed', 'Failed'
        UNKNOWN = 'unknown', 'Unknown'
        SKIPPED = 'skipped', 'Skipped'
        # Legacy — migrated to submitted; kept for old rows/readers.
        SENT = 'sent', 'Sent'

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='guardian_deliveries',
    )
    parent = models.ForeignKey(
        'students.Parent',
        on_delete=models.CASCADE,
        related_name='deliveries',
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='guardian_deliveries',
    )
    event_type = models.CharField(max_length=40, choices=EventType.choices)
    channel = models.CharField(max_length=10, choices=Channel.choices)
    status = models.CharField(max_length=20, choices=Status.choices)
    recipient_address = models.CharField(max_length=255, blank=True, default='')
    body_preview = models.CharField(max_length=500, blank=True, default='')
    body_text = models.TextField(blank=True, default='')
    provider_message_id = models.CharField(max_length=100, blank=True, default='', db_index=True)
    provider_status = models.CharField(max_length=40, blank=True, default='')
    skip_reason = models.CharField(max_length=200, blank=True, default='')
    error_message = models.CharField(max_length=500, blank=True, default='')
    user_error_message = models.CharField(max_length=240, blank=True, default='')
    idempotency_key = models.CharField(max_length=120, unique=True)
    source_delivery = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resend_attempts',
    )
    segments = models.PositiveSmallIntegerField(default=0)
    credits_charged = models.PositiveIntegerField(default=0)
    credits_refunded = models.PositiveIntegerField(default=0)
    status_updated_at = models.DateTimeField(null=True, blank=True)

    # --- v4.1 messaging economics (§2.6.5) -------------------------------
    # Snapshots are written at send time; pre-v4.1 rows keep nulls and must be
    # reported as "unpriced" rather than re-valued with today's config.
    billing_classification = models.CharField(
        max_length=20,
        choices=BillingClassification.choices,
        default=BillingClassification.PAID,
        db_index=True,
    )
    allowance = models.ForeignKey(
        'communications.MessagingAllowancePolicy',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='guardian_deliveries',
    )
    provider_cost_snapshot_ghs = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Provider cost per unit at send time × units.',
    )
    school_unit_price_snapshot_ghs = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Reference sell price per unit at send time × units.',
    )
    encoding_snapshot = models.CharField(max_length=20, blank=True, default='')
    segment_limit_snapshot = models.JSONField(default=dict, blank=True)
    provider_units_reported = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Units the provider reported, when available — for variance only.',
    )
    unbilled = models.BooleanField(
        default=False,
        help_text='Accepted by the provider but the school debit could not be written.',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['school', 'event_type', '-created_at']),
            models.Index(fields=['school', 'status', '-created_at']),
            models.Index(fields=['parent', '-created_at']),
            models.Index(fields=['student', '-created_at']),
            models.Index(fields=['channel', 'status', 'status_updated_at']),
            models.Index(fields=['billing_classification', 'channel', '-created_at']),
            models.Index(fields=['school', 'billing_classification', '-created_at']),
            models.Index(fields=['unbilled', '-created_at']),
        ]

    def __str__(self):
        return f'{self.event_type}/{self.channel} → {self.parent_id} ({self.status})'

    @property
    def is_paid_traffic(self) -> bool:
        return self.billing_classification == BillingClassification.PAID

    @property
    def net_credits_charged(self) -> int:
        return max(0, int(self.credits_charged or 0) - int(self.credits_refunded or 0))


class PlatformOutboundDelivery(BaseModel):
    """Platform-funded outbound attempt — OTP SMS/email, staff email, broadcasts.

    Hard rule (v4 invariant 4, enforced structurally): rows here are NEVER
    linked to a ``usage_debit`` ledger entry. ``CreditLedgerEntry`` has no FK to
    this model, so a school wallet can never be debited for this traffic.
    """

    BillingClassification = BillingClassification

    class Purpose(models.TextChoices):
        OTP_SMS = 'otp_sms', 'Auth OTP SMS'
        OTP_EMAIL = 'otp_email', 'Auth OTP email'
        STAFF_EMAIL = 'staff_email', 'Staff notification email'
        PLATFORM_BROADCAST = 'platform_broadcast', 'Platform broadcast'
        OTHER = 'other', 'Other'

    class Channel(models.TextChoices):
        SMS = 'sms', 'SMS'
        EMAIL = 'email', 'Email'

    class Provider(models.TextChoices):
        ARKESEL = 'arkesel', 'Arkesel'
        SES = 'ses', 'Amazon SES'
        RESEND = 'resend', 'Resend (legacy)'
        DJANGO = 'django', 'Django mail backend'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        DELIVERED = 'delivered', 'Delivered'
        FAILED = 'failed', 'Failed'
        UNKNOWN = 'unknown', 'Unknown'
        SKIPPED = 'skipped', 'Skipped'

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='platform_outbound_deliveries',
        help_text='Nullable — OTP traffic may precede any school context.',
    )
    purpose = models.CharField(max_length=40, choices=Purpose.choices)
    channel = models.CharField(max_length=10, choices=Channel.choices)
    provider = models.CharField(max_length=20, choices=Provider.choices, default=Provider.OTHER)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    recipient_address = models.CharField(max_length=255, blank=True, default='')
    provider_message_id = models.CharField(max_length=100, blank=True, default='', db_index=True)
    provider_status = models.CharField(max_length=40, blank=True, default='')
    segments = models.PositiveSmallIntegerField(default=0)
    units = models.PositiveIntegerField(default=1)
    billing_classification = models.CharField(
        max_length=20,
        choices=BillingClassification.choices,
        default=BillingClassification.FREE,
    )
    provider_cost_snapshot_ghs = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        null=True,
        blank=True,
    )
    encoding_snapshot = models.CharField(max_length=20, blank=True, default='')
    segment_limit_snapshot = models.JSONField(default=dict, blank=True)
    error_message = models.CharField(max_length=500, blank=True, default='')
    idempotency_key = models.CharField(max_length=191, unique=True)
    metadata = models.JSONField(default=dict, blank=True)
    status_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['purpose', 'channel', '-created_at']),
            models.Index(fields=['channel', 'status', '-created_at']),
            models.Index(fields=['school', '-created_at']),
        ]

    def __str__(self):
        return f'{self.purpose}/{self.channel} ({self.status})'


class ResendWebhookEvent(BaseModel):
    """Received Resend (Svix) webhook event — idempotency and ops visibility."""

    event_id = models.CharField(max_length=191, unique=True)
    event_type = models.CharField(max_length=60, blank=True, default='')
    provider_message_id = models.CharField(max_length=100, blank=True, default='', db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    signature_valid = models.BooleanField(default=False)
    processed = models.BooleanField(default=False)
    matched_delivery_type = models.CharField(max_length=40, blank=True, default='')
    matched_delivery_id = models.CharField(max_length=64, blank=True, default='')
    error = models.CharField(max_length=500, blank=True, default='')
    received_at = models.DateTimeField()

    class Meta:
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['event_type', '-received_at']),
            models.Index(fields=['processed', '-received_at']),
        ]

    def __str__(self):
        return f'{self.event_type} {self.event_id}'


class GuardianMessageTemplate(BaseModel):
    """Per-school override of guardian SMS/email copy for one event type.

    Blank fields fall back to system defaults. SMS body is the part after the
    fixed ``{Sender} [School]:`` prefix.
    """

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='guardian_message_templates',
    )
    event_type = models.CharField(max_length=40, choices=GuardianDelivery.EventType.choices)
    sms_body = models.TextField(blank=True, default='')
    sms_body_all_time = models.TextField(
        blank=True,
        default='',
        help_text='Debt reminder all-time variant only; ignored for other events.',
    )
    email_subject = models.CharField(max_length=200, blank=True, default='')
    email_text = models.TextField(blank=True, default='')
    email_html = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['event_type']
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'event_type'],
                name='uniq_guardian_message_template_school_event',
            ),
        ]
        indexes = [
            models.Index(fields=['school', 'event_type']),
        ]

    def __str__(self):
        return f'{self.school_id}:{self.event_type}'
