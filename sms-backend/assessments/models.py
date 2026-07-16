from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

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

    level = models.OneToOneField(
        'academics.Level',
        on_delete=models.CASCADE,
        related_name='assessment_config',
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

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Assessment config for {self.level}'


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
    pass


class AssessmentItemScore(BaseModel):
    pass


class StudentResult(BaseModel):
    pass


class SubjectScore(BaseModel):
    pass


class Report(BaseModel):
    pass


# tentative
class CorrectionRequest(BaseModel):
    pass
