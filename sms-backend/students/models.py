from django.db import models

from shared.models import BaseModel


class Student(BaseModel):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='students',
    )
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class ClassEnrollment(BaseModel):
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='enrollments',
    )
    term = models.ForeignKey(
        'schools.Term',
        on_delete=models.CASCADE,
        related_name='enrollments',
    )
    class_level = models.ForeignKey(
        'academics.ClassLevel',
        on_delete=models.PROTECT,
        related_name='enrollments',
    )
    is_new_student = models.BooleanField(
        default=False,
        help_text='True when this is the student\'s first term at the school.',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'term'],
                name='unique_student_enrollment_per_term',
            ),
        ]

    def __str__(self):
        return f'{self.student} ({self.term})'
