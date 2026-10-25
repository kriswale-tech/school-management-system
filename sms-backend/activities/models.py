from django.db import models

from shared.models import BaseModel


class Activity(BaseModel):
    """A school event worth showing on the admin activity feed.

    The summary is stored when the event is written so later renames do not
    rewrite history. Targets are plain ids so deleting a student or class
    does not delete the feed row.
    """

    class Verb(models.TextChoices):
        SCORES_PUBLISHED = 'scores_published', 'Scores published'
        STUDENTS_APPROVED = 'students_approved', 'Students approved'
        STUDENT_REJECTED = 'student_rejected', 'Student rejected'
        REOPEN_REQUESTED = 'reopen_requested', 'Reopen requested'
        REPORTS_RELEASED = 'reports_released', 'Reports released'
        CORRECTION_SENT = 'correction_sent', 'Correction sent'
        CORRECTION_APPLIED = 'correction_applied', 'Correction applied'
        REOPEN_DECLINED = 'reopen_declined', 'Reopen declined'
        PAYMENT_RECORDED = 'payment_recorded', 'Payment recorded'
        FEE_STRUCTURE_APPLIED = 'fee_structure_applied', 'Fee structure applied'
        ADVANCE_CREATED = 'advance_created', 'Advance created'
        CLASS_TEACHER_ASSIGNED = 'class_teacher_assigned', 'Class teacher assigned'
        SUBJECT_TEACHER_ASSIGNED = 'subject_teacher_assigned', 'Subject teacher assigned'
        SUBJECT_GROUP_PLACED = 'subject_group_placed', 'Subject group placed'
        STUDENT_ENROLLED = 'student_enrolled', 'Student enrolled'
        STUDENT_LEFT = 'student_left', 'Student left'
        STUDENT_REACTIVATED = 'student_reactivated', 'Student reactivated'

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='activities',
    )
    actor = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
    )
    actor_name = models.CharField(max_length=255, blank=True)
    verb = models.CharField(max_length=40, choices=Verb.choices)
    summary = models.CharField(max_length=500)
    href = models.CharField(max_length=500, blank=True)
    term = models.ForeignKey(
        'schools.Term',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
    )
    target_kind = models.CharField(max_length=40, blank=True)
    target_id = models.UUIDField(null=True, blank=True)
    stream = models.ForeignKey(
        'academics.ClassStream',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
    )
    teaching_assignment = models.ForeignKey(
        'teachers.TeachingAssignment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['school', '-created_at']),
            models.Index(fields=['school', 'term', '-created_at']),
        ]

    def __str__(self):
        return self.summary
