from django.core.exceptions import ValidationError
from django.db import models

from shared.models import BaseModel


class Level(BaseModel):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='levels',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
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

    def __str__(self):
        return self.name


class ClassLevel(BaseModel):
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
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
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
        if self.level_id and self.school_id and self.level.school_id != self.school_id:
            raise ValidationError({'school': 'Must match the selected level school.'})

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


class Subject(BaseModel):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='subjects',
    )
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

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


class ClassSubject(BaseModel):
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
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['class_level', 'subject'],
                name='unique_subject_per_class_level',
            ),
        ]

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
