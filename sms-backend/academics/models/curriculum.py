from django.db import models

from academics.curriculum_guard import ImmutableCurriculumMixin
from shared.models import BaseModel


class Curriculum(ImmutableCurriculumMixin, BaseModel):
    """Standard curriculum template (source of truth for school provisioning)."""

    name = models.CharField(max_length=255)
    code = models.SlugField(max_length=50)
    version = models.CharField(max_length=20, default='2024')
    is_active = models.BooleanField(
        default=True,
        help_text='When true, this version is used for new school provisioning.',
    )

    class Meta:
        ordering = ['code', '-version']
        constraints = [
            models.UniqueConstraint(
                fields=['code', 'version'],
                name='unique_curriculum_code_version',
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.version})'


class CurriculumLevel(ImmutableCurriculumMixin, BaseModel):
    class SubjectScope(models.TextChoices):
        LEVEL = 'level', 'Shared across classes'
        CLASS = 'class', 'Configured per class'

    curriculum = models.ForeignKey(
        Curriculum,
        on_delete=models.CASCADE,
        related_name='levels',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    subject_scope = models.CharField(
        max_length=10,
        choices=SubjectScope.choices,
        default=SubjectScope.LEVEL,
    )
    allows_custom_classes = models.BooleanField(
        default=False,
        help_text='When true, schools may add their own classes under this level.',
    )
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ['order', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['curriculum', 'name'],
                name='unique_curriculum_level_name',
            ),
        ]

    def __str__(self):
        return self.name


class CurriculumClassLevel(ImmutableCurriculumMixin, BaseModel):
    level = models.ForeignKey(
        CurriculumLevel,
        on_delete=models.CASCADE,
        related_name='class_levels',
    )
    name = models.CharField(max_length=255)
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ['order', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['level', 'name'],
                name='unique_curriculum_class_level_name',
            ),
        ]

    def __str__(self):
        return self.name


class CurriculumSubject(ImmutableCurriculumMixin, BaseModel):
    level = models.ForeignKey(
        CurriculumLevel,
        on_delete=models.CASCADE,
        related_name='subjects',
    )
    curriculum_class_level = models.ForeignKey(
        CurriculumClassLevel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subjects',
        help_text='When set, this subject applies only to the linked template class.',
    )
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['level', 'name'],
                condition=models.Q(curriculum_class_level__isnull=True),
                name='unique_level_scoped_curriculum_subject_name',
            ),
            models.UniqueConstraint(
                fields=['curriculum_class_level', 'name'],
                condition=models.Q(curriculum_class_level__isnull=False),
                name='unique_class_scoped_curriculum_subject_name',
            ),
        ]

    def __str__(self):
        return self.name
