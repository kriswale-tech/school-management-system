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


class GuardianDelivery(BaseModel):
    """Outbound SMS/email attempt to a Parent contact (not a staff inbox row)."""

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
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'
        SKIPPED = 'skipped', 'Skipped'

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
    provider_message_id = models.CharField(max_length=100, blank=True, default='')
    skip_reason = models.CharField(max_length=200, blank=True, default='')
    error_message = models.CharField(max_length=500, blank=True, default='')
    idempotency_key = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['school', 'event_type', '-created_at']),
            models.Index(fields=['parent', '-created_at']),
            models.Index(fields=['student', '-created_at']),
        ]

    def __str__(self):
        return f'{self.event_type}/{self.channel} → {self.parent_id} ({self.status})'
