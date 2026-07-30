from django.core.exceptions import ValidationError
from django.db import models

from accounts.models import SchoolMembership, User
from shared.models import BaseModel


def validate_teacher_for_term(teacher_id, term) -> None:
    """A teacher must hold an active teacher role in the school owning the term."""
    membership = SchoolMembership.objects.filter(
        user_id=teacher_id,
        school_id=term.school_id,
        is_active=True,
    ).first()

    if membership is None:
        raise ValidationError({'teacher': 'Teacher must belong to the term school.'})

    if membership.role != User.RoleChoices.TEACHER:
        raise ValidationError({'teacher': 'User must have the teacher role.'})


class ClassTeacher(BaseModel):
    teacher = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='class_teacher_assignments',
    )
    class_level = models.ForeignKey(
        'academics.ClassLevel',
        on_delete=models.CASCADE,
        related_name='class_teachers',
    )
    stream = models.ForeignKey(
        'academics.ClassStream',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='class_teachers',
    )
    term = models.ForeignKey(
        'schools.Term',
        on_delete=models.CASCADE,
        related_name='class_teachers',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['class_level', 'term'],
                condition=models.Q(stream__isnull=True),
                name='unique_class_teacher_per_class_term',
            ),
            models.UniqueConstraint(
                fields=['class_level', 'stream', 'term'],
                condition=models.Q(stream__isnull=False),
                name='unique_class_teacher_per_stream_term',
            ),
        ]

    def clean(self):
        super().clean()

        if self.teacher_id and self.term_id:
            validate_teacher_for_term(self.teacher_id, self.term)

        if self.class_level_id and self.term_id:
            if self.class_level.school_id != self.term.school_id:
                raise ValidationError({'class_level': 'Class must belong to the term school.'})

        if self.stream_id and self.class_level_id:
            if self.stream.class_level_id != self.class_level_id:
                raise ValidationError({'stream': 'Stream must belong to the selected class.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        target = self.stream.full_name if self.stream_id else self.class_level.name
        return f'{self.teacher.get_full_name()} - {target}'


class TeachingAssignment(BaseModel):
    teacher = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='teaching_assignments',
    )
    class_subject = models.ForeignKey(
        'academics.ClassSubject',
        on_delete=models.CASCADE,
        related_name='teaching_assignments',
    )
    stream = models.ForeignKey(
        'academics.ClassStream',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='teaching_assignments',
    )
    subject_group = models.ForeignKey(
        'academics.SubjectGroup',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='teaching_assignments',
    )
    term = models.ForeignKey(
        'schools.Term',
        on_delete=models.CASCADE,
        related_name='teaching_assignments',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['class_subject', 'term'],
                condition=models.Q(stream__isnull=True, subject_group__isnull=True),
                name='unique_teaching_assignment_per_class_subject_term',
            ),
            models.UniqueConstraint(
                fields=['class_subject', 'stream', 'term'],
                condition=models.Q(stream__isnull=False, subject_group__isnull=True),
                name='unique_teaching_assignment_per_stream_term',
            ),
            models.UniqueConstraint(
                fields=['class_subject', 'subject_group', 'term'],
                condition=models.Q(subject_group__isnull=False),
                name='unique_teaching_assignment_per_subject_group_term',
            ),
        ]

    def clean(self):
        super().clean()

        if self.teacher_id and self.term_id:
            validate_teacher_for_term(self.teacher_id, self.term)

        if self.class_subject_id and self.term_id:
            if self.class_subject.school_id != self.term.school_id:
                raise ValidationError({
                    'class_subject': 'Class subject must belong to the term school.',
                })

        if self.stream_id and self.class_subject_id:
            if self.stream.class_level_id != self.class_subject.class_level_id:
                raise ValidationError({'stream': 'Stream must belong to the class subject class.'})

        if self.subject_group_id and self.class_subject_id:
            if self.subject_group.class_subject_id != self.class_subject_id:
                raise ValidationError({
                    'subject_group': 'Subject group must belong to the class subject.',
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f'{self.teacher.get_full_name()} - '
            f'{self.class_subject.class_level.name} {self.class_subject.subject.name}'
        )
