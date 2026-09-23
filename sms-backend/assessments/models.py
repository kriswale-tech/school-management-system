from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from assessments.storage import report_storage, report_upload_to
from shared.models import BaseModel


class AssessmentConfig(BaseModel):
    class ResultType(models.TextChoices):
        POSITION = 'position', 'Position'
        GRADE = 'grade', 'Grade'
        GRADE_AND_POSITION = 'grade_and_position', 'Grade and Position'

    class GradeType(models.TextChoices):
        LETTER = 'letter', 'Letter grades (A-F)'
        NUMERICAL = 'numerical', 'Numerical grades (1-9)'

    GRADE_RESULT_TYPES = frozenset({
        ResultType.GRADE,
        ResultType.GRADE_AND_POSITION,
    })
    POSITION_RESULT_TYPES = frozenset({
        ResultType.POSITION,
        ResultType.GRADE_AND_POSITION,
    })

    level = models.ForeignKey(
        'academics.Level',
        on_delete=models.CASCADE,
        related_name='assessment_configs',
    )
    term = models.ForeignKey(
        'schools.Term',
        on_delete=models.CASCADE,
        related_name='assessment_configs',
    )
    continuous_assessment_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('40.00'),
        help_text='Continuous assessment weight as a percentage of the total.',
    )
    exam_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('60.00'),
        help_text='Exam weight as a percentage of the total.',
    )
    result_type = models.CharField(
        max_length=30,
        choices=ResultType.choices,
        default=ResultType.GRADE_AND_POSITION,
    )
    grade_type = models.CharField(
        max_length=20,
        choices=GradeType.choices,
        null=True,
        blank=True,
        help_text='Required when result type includes grades.',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['level', 'term'],
                name='unique_assessment_config_per_level_term',
            ),
            models.CheckConstraint(
                condition=Q(continuous_assessment_weight__gte=0) & Q(exam_weight__gte=0),
                name='assessment_config_weights_non_negative',
            ),
            models.CheckConstraint(
                condition=Q(continuous_assessment_weight=100 - F('exam_weight')),
                name='assessment_config_weights_sum_100',
            ),
        ]

    def uses_grades(self):
        return self.result_type in self.GRADE_RESULT_TYPES

    def uses_position(self):
        return self.result_type in self.POSITION_RESULT_TYPES

    def clean(self):
        super().clean()
        errors = {}

        ca = self.continuous_assessment_weight
        exam = self.exam_weight
        if ca is not None and exam is not None:
            if ca < 0 or exam < 0:
                errors['continuous_assessment_weight'] = 'Weights must be non-negative.'
            elif ca + exam != Decimal('100'):
                errors['continuous_assessment_weight'] = (
                    'Continuous assessment and exam weights must sum to 100.'
                )

        if self.uses_grades():
            if not self.grade_type:
                errors['grade_type'] = (
                    'Grade type is required when result type includes grades.'
                )
        elif self.grade_type:
            errors['grade_type'] = (
                'Grade type must be empty when result type is position only.'
            )

        if (
            self.level_id
            and self.term_id
            and self.level.school_id != self.term.school_id
        ):
            errors['term'] = 'Term must belong to the same school as the level.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Assessment config for {self.level} ({self.term})'


class GradeBand(BaseModel):
    assessment_config = models.ForeignKey(
        AssessmentConfig,
        on_delete=models.CASCADE,
        related_name='grade_bands',
    )
    grade = models.CharField(
        max_length=10,
        help_text='Letter (A-F) or numerical (1-9) grade label.',
    )
    min_score = models.PositiveSmallIntegerField()
    max_score = models.PositiveSmallIntegerField()
    remark = models.CharField(max_length=100)
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ['-min_score', 'order', 'grade']
        constraints = [
            models.UniqueConstraint(
                fields=['assessment_config', 'grade'],
                name='unique_grade_label_per_assessment_config',
            ),
            models.CheckConstraint(
                condition=Q(min_score__lte=F('max_score')),
                name='grade_band_min_lte_max',
            ),
            models.CheckConstraint(
                condition=Q(max_score__lte=100),
                name='grade_band_max_score_lte_100',
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.min_score is not None and self.max_score is not None:
            if self.min_score > self.max_score:
                errors['min_score'] = 'Minimum score cannot exceed maximum score.'
            if self.max_score > 100:
                errors['max_score'] = 'Maximum score cannot exceed 100.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.grade} ({self.min_score}–{self.max_score})'


class AssessmentItem(BaseModel):
    """A continuous-assessment column for one teaching assignment / term."""

    teaching_assignment = models.ForeignKey(
        'teachers.TeachingAssignment',
        on_delete=models.CASCADE,
        related_name='assessment_items',
    )
    name = models.CharField(max_length=100)
    max_marks = models.DecimalField(max_digits=7, decimal_places=2)
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ['order', 'created_at', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['teaching_assignment', 'name'],
                name='unique_assessment_item_name_per_assignment',
            ),
            models.CheckConstraint(
                condition=Q(max_marks__gt=0),
                name='assessment_item_max_marks_positive',
            ),
        ]

    def clean(self):
        super().clean()
        if self.max_marks is not None and self.max_marks <= 0:
            raise ValidationError({'max_marks': 'Max marks must be greater than 0.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} ({self.max_marks})'


class AssessmentItemScore(BaseModel):
    assessment_item = models.ForeignKey(
        AssessmentItem,
        on_delete=models.CASCADE,
        related_name='scores',
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='assessment_item_scores',
    )
    mark = models.DecimalField(max_digits=7, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['assessment_item', 'student'],
                name='unique_score_per_student_assessment_item',
            ),
            models.CheckConstraint(
                condition=Q(mark__gte=0),
                name='assessment_item_score_mark_non_negative',
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.mark is not None and self.mark < 0:
            errors['mark'] = 'Mark cannot be negative.'
        if (
            self.assessment_item_id
            and self.mark is not None
            and self.assessment_item.max_marks is not None
            and self.mark > self.assessment_item.max_marks
        ):
            errors['mark'] = (
                f'Mark cannot exceed max marks ({self.assessment_item.max_marks}).'
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.student_id} — {self.assessment_item_id}: {self.mark}'


class SubjectScore(BaseModel):
    """Per-student exam + publish state for a teaching assignment."""

    teaching_assignment = models.ForeignKey(
        'teachers.TeachingAssignment',
        on_delete=models.CASCADE,
        related_name='subject_scores',
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='subject_scores',
    )
    exam_mark = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Exam mark out of 100. Null until the exam is recorded.',
    )
    is_published = models.BooleanField(
        default=False,
        help_text='True when the subject teacher has released this result to the class teacher.',
    )
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['teaching_assignment', 'student'],
                name='unique_subject_score_per_student_assignment',
            ),
            models.CheckConstraint(
                condition=Q(exam_mark__isnull=True)
                | (Q(exam_mark__gte=0) & Q(exam_mark__lte=100)),
                name='subject_score_exam_mark_0_to_100',
            ),
        ]

    def clean(self):
        super().clean()
        if self.exam_mark is not None:
            if self.exam_mark < 0 or self.exam_mark > 100:
                raise ValidationError({'exam_mark': 'Exam mark must be between 0 and 100.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.student_id} exam={self.exam_mark} published={self.is_published}'


class StudentResult(BaseModel):
    """Class-teacher approval state for a student in a class/stream for a term."""

    class Status(models.TextChoices):
        AWAITING_APPROVAL = 'awaiting_approval', 'Awaiting approval'
        APPROVED = 'approved', 'Approved'
        RELEASED = 'released', 'Released'
        NEEDS_CORRECTION = 'needs_correction', 'Needs correction'

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='assessment_results',
    )
    term = models.ForeignKey(
        'schools.Term',
        on_delete=models.CASCADE,
        related_name='student_assessment_results',
    )
    class_level = models.ForeignKey(
        'academics.ClassLevel',
        on_delete=models.CASCADE,
        related_name='student_assessment_results',
    )
    stream = models.ForeignKey(
        'academics.ClassStream',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='student_assessment_results',
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.AWAITING_APPROVAL,
    )
    remarks = models.TextField(blank=True, default='')
    conduct = models.TextField(blank=True, default='')
    attitude = models.TextField(blank=True, default='')
    interest = models.TextField(blank=True, default='')
    head_teacher_remarks = models.TextField(blank=True, default='')
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_student_results',
    )
    released_at = models.DateTimeField(null=True, blank=True)
    released_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='released_student_results',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'term', 'class_level'],
                condition=Q(stream__isnull=True),
                name='unique_student_result_whole_class_term',
            ),
            models.UniqueConstraint(
                fields=['student', 'term', 'class_level', 'stream'],
                condition=Q(stream__isnull=False),
                name='unique_student_result_stream_term',
            ),
        ]

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.student_id} {self.status}'


class Report(BaseModel):
    """Stored PDF report card for a student in a stream/term."""

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='assessment_reports',
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='assessment_reports',
    )
    stream = models.ForeignKey(
        'academics.ClassStream',
        on_delete=models.CASCADE,
        related_name='assessment_reports',
    )
    term = models.ForeignKey(
        'schools.Term',
        on_delete=models.CASCADE,
        related_name='assessment_reports',
    )
    file = models.FileField(
        storage=report_storage,
        upload_to=report_upload_to,
        blank=True,
        max_length=500,
    )
    generated_at = models.DateTimeField(null=True, blank=True)
    generated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_assessment_reports',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'student', 'stream', 'term'],
                name='unique_report_student_stream_term',
            ),
        ]

    def __str__(self):
        return f'report {self.student_id} {self.term_id}'


class CorrectionRequest(BaseModel):
    """Audit + workflow for send-back / reopen of selected subjects."""

    class Kind(models.TextChoices):
        REJECT = 'reject', 'Reject'
        REOPEN = 'reopen', 'Reopen'
        REOPEN_REQUEST = 'reopen_request', 'Reopen request'

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        DECLINED = 'declined', 'Declined'
        APPLIED = 'applied', 'Applied'
        RESOLVED = 'resolved', 'Resolved'

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='correction_requests',
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='correction_requests',
    )
    stream = models.ForeignKey(
        'academics.ClassStream',
        on_delete=models.CASCADE,
        related_name='correction_requests',
    )
    term = models.ForeignKey(
        'schools.Term',
        on_delete=models.CASCADE,
        related_name='correction_requests',
    )
    kind = models.CharField(max_length=32, choices=Kind.choices)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.OPEN,
    )
    reason = models.TextField()
    previous_result_status = models.CharField(max_length=32, blank=True, default='')
    raised_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='raised_correction_requests',
    )
    raised_at = models.DateTimeField()
    reviewed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_correction_requests',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-raised_at']

    def __str__(self):
        return f'{self.kind} {self.status} {self.student_id}'


class CorrectionRequestSubject(BaseModel):
    correction_request = models.ForeignKey(
        CorrectionRequest,
        on_delete=models.CASCADE,
        related_name='subjects',
    )
    teaching_assignment = models.ForeignKey(
        'teachers.TeachingAssignment',
        on_delete=models.CASCADE,
        related_name='correction_request_subjects',
    )
    subject_label = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['correction_request', 'teaching_assignment'],
                name='unique_correction_request_teaching_assignment',
            ),
        ]


class CorrectionRequestEvent(BaseModel):
    """Append-only audit log for a correction request."""

    correction_request = models.ForeignKey(
        CorrectionRequest,
        on_delete=models.CASCADE,
        related_name='events',
    )
    event_type = models.CharField(max_length=64)
    detail = models.JSONField(default=dict, blank=True)
    actor = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='correction_request_events',
    )
    occurred_at = models.DateTimeField()

    class Meta:
        ordering = ['occurred_at', 'created_at']


# tentative stub removed — CorrectionRequest is implemented above
