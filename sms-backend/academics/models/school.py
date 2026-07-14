from django.core.exceptions import ValidationError
from django.db import models

from academics.mixins import SystemGeneratedRecordMixin
from shared.models import BaseModel


class Level(SystemGeneratedRecordMixin, BaseModel):
    class SubjectScope(models.TextChoices):
        LEVEL = 'level', 'Shared across classes'
        CLASS = 'class', 'Configured per class'

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='levels',
    )
    curriculum_level = models.ForeignKey(
        'academics.CurriculumLevel',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='school_levels',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_system_generated = models.BooleanField(default=False)
    subject_scope = models.CharField(
        max_length=10,
        choices=SubjectScope.choices,
        default=SubjectScope.LEVEL,
    )
    allows_custom_classes = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(
        default=1,
        help_text='Display order within the school.',
    )

    class Meta:
        ordering = ['order', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'name'],
                name='unique_level_name_per_school',
            ),
        ]

    def clean(self):
        super().clean()
        if self.is_system_generated and not self.curriculum_level_id:
            raise ValidationError({
                'curriculum_level': 'Required for system-generated levels.',
            })
        if not self.is_system_generated and self.curriculum_level_id:
            raise ValidationError({
                'curriculum_level': 'Custom levels cannot reference the master curriculum.',
            })

    def uses_per_class_subjects(self):
        return self.subject_scope == self.SubjectScope.CLASS

    def __str__(self):
        return self.name


class ClassLevel(SystemGeneratedRecordMixin, BaseModel):
    level = models.ForeignKey(
        'Level',
        on_delete=models.CASCADE,
        related_name='class_levels',
    )
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='class_levels',
    )
    curriculum_class_level = models.ForeignKey(
        'academics.CurriculumClassLevel',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='school_class_levels',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_system_generated = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(
        default=1,
        help_text='Display order within the level.',
    )

    class Meta:
        ordering = ['level__order', 'order', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'level', 'name'],
                name='unique_class_level_name_per_level',
            ),
        ]

    def clean(self):
        super().clean()
        if self.level_id and self.school_id and self.level.school_id != self.school_id:
            raise ValidationError({'school': 'Must match the selected level school.'})
        if self.is_system_generated and not self.curriculum_class_level_id:
            raise ValidationError({
                'curriculum_class_level': 'Required for system-generated classes.',
            })
        if not self.is_system_generated and self.curriculum_class_level_id:
            raise ValidationError({
                'curriculum_class_level': 'Custom classes cannot reference the master curriculum.',
            })

    def save(self, *args, **kwargs):
        if self.level_id:
            self.school_id = self.level.school_id
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ClassStream(BaseModel):
    class_level = models.ForeignKey(
        'ClassLevel',
        on_delete=models.CASCADE,
        related_name='streams',
    )
    name = models.CharField(
        max_length=20,
        blank=True,
        help_text='Leave blank for the default stream, e.g. A, B, Lily.',
    )
    description = models.TextField(null=True, blank=True)
    is_default = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    capacity = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['class_level', 'name'],
                name='unique_stream_name_per_class_level',
            ),
            models.UniqueConstraint(
                fields=['class_level'],
                condition=models.Q(is_default=True),
                name='unique_default_stream_per_class_level',
            ),
        ]

    def clean(self):
        if self.is_default:
            if self.name:
                raise ValidationError({'name': 'Default streams should not have a name.'})
        elif not self.name:
            raise ValidationError({'name': 'Required for non-default streams.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def school(self):
        return self.class_level.school

    @property
    def full_name(self):
        if self.is_default:
            return self.class_level.name
        return f'{self.class_level.name} {self.name}'

    def __str__(self):
        return self.full_name


class Subject(SystemGeneratedRecordMixin, BaseModel):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='subjects',
    )
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_system_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'name'],
                name='unique_subject_name_per_school',
            ),
        ]

    def __str__(self):
        return self.name


class LevelSubject(SystemGeneratedRecordMixin, BaseModel):
    """Subject membership on a level (catalog), independent of class assignment."""

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='level_subjects',
    )
    level = models.ForeignKey(
        'Level',
        on_delete=models.CASCADE,
        related_name='level_subjects',
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='level_subjects',
    )
    curriculum_subject = models.ForeignKey(
        'academics.CurriculumSubject',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='school_level_subjects',
    )
    is_active = models.BooleanField(default=True)
    is_system_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ['subject__name']
        constraints = [
            models.UniqueConstraint(
                fields=['level', 'subject'],
                name='unique_subject_per_level',
            ),
        ]

    def clean(self):
        super().clean()
        if self.level_id and self.school_id and self.level.school_id != self.school_id:
            raise ValidationError({'school': 'Must match the selected level school.'})
        if self.subject_id and self.school_id and self.subject.school_id != self.school_id:
            raise ValidationError({'school': 'Must match the selected subject school.'})
        if self.is_system_generated and not self.curriculum_subject_id:
            raise ValidationError({
                'curriculum_subject': 'Required for system-generated level subjects.',
            })
        if not self.is_system_generated and self.curriculum_subject_id:
            raise ValidationError({
                'curriculum_subject': 'Custom level subjects cannot reference the master curriculum.',
            })

    def save(self, *args, **kwargs):
        if self.level_id:
            self.school_id = self.level.school_id
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.level.name} - {self.subject.name}'


class ClassSubject(SystemGeneratedRecordMixin, BaseModel):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='class_subjects',
    )
    class_level = models.ForeignKey(
        'ClassLevel',
        on_delete=models.CASCADE,
        related_name='class_subjects',
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='class_subjects',
    )
    curriculum_subject = models.ForeignKey(
        'academics.CurriculumSubject',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='school_class_subjects',
    )
    is_active = models.BooleanField(default=True)
    is_system_generated = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['class_level', 'subject'],
                name='unique_subject_per_class_level',
            ),
        ]

    def clean(self):
        super().clean()
        if self.class_level_id and self.subject_id:
            if not LevelSubject.objects.filter(
                level_id=self.class_level.level_id,
                subject_id=self.subject_id,
            ).exists():
                raise ValidationError({
                    'subject': 'Subject must belong to the class level first.',
                })
        if self.is_system_generated and not self.curriculum_subject_id:
            raise ValidationError({
                'curriculum_subject': 'Required for system-generated class subjects.',
            })
        if not self.is_system_generated and self.curriculum_subject_id:
            raise ValidationError({
                'curriculum_subject': 'Custom class subjects cannot reference the master curriculum.',
            })

    def delete(self, *args, **kwargs):
        # Class-subject links are removable even when provisioned; the Subject remains.
        return models.Model.delete(self, *args, **kwargs)

    def __str__(self):
        return f'{self.class_level.name} - {self.subject.name}'


class SubjectGroup(BaseModel):
    class_subject = models.ForeignKey(
        ClassSubject,
        on_delete=models.CASCADE,
        related_name='groups',
    )
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['class_subject', 'name'],
                name='unique_subject_group_per_class_subject',
            ),
        ]

    def __str__(self):
        return f'{self.class_subject} - {self.name}'


class StudentSubjectGroup(BaseModel):
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='subject_group_assignments',
    )
    class_subject = models.ForeignKey(
        ClassSubject,
        on_delete=models.CASCADE,
        related_name='student_group_assignments',
    )
    subject_group = models.ForeignKey(
        SubjectGroup,
        on_delete=models.CASCADE,
        related_name='student_assignments',
    )
    academic_year = models.ForeignKey(
        'schools.AcademicYear',
        on_delete=models.CASCADE,
        related_name='student_subject_groups',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'class_subject', 'academic_year'],
                name='unique_student_class_subject_per_academic_year',
            ),
        ]

    def clean(self):
        if self.subject_group_id and self.class_subject_id:
            if self.subject_group.class_subject_id != self.class_subject_id:
                raise ValidationError({
                    'subject_group': 'Must belong to the selected class subject.',
                })

        if self.academic_year_id and self.class_subject_id:
            if self.academic_year.school_id != self.class_subject.school_id:
                raise ValidationError({
                    'academic_year': 'Must belong to the same school as the class subject.',
                })

    def save(self, *args, **kwargs):
        if self.subject_group_id:
            self.class_subject_id = self.subject_group.class_subject_id
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.student_id} - {self.subject_group.name}'
