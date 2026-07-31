from django.core.exceptions import ValidationError
from django.db import models

from shared.models import BaseModel


class Parent(BaseModel):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='parents',
    )
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15)
    phone_number_alt = models.CharField(max_length=15, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    address = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'phone_number'],
                name='unique_parent_phone_per_school',
            ),
        ]

    def __str__(self):
        return self.name


class Student(BaseModel):
    class GenderChoices(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        OTHER = 'other', 'Other'

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='students',
    )
    student_id = models.CharField(max_length=255)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    other_names = models.CharField(max_length=255, blank=True, default='')
    gender = models.CharField(max_length=10, choices=GenderChoices.choices)
    date_of_birth = models.DateField()
    admission_date = models.DateField()
    parents = models.ManyToManyField(
        'students.Parent',
        related_name='students',
        through='students.StudentParent',
    )

    class Meta:
        ordering = ['last_name', 'first_name']
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'student_id'],
                name='unique_student_id_per_school',
            ),
        ]

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class StudentParent(BaseModel):
    class RelationshipChoices(models.TextChoices):
        FATHER = 'father', 'Father'
        MOTHER = 'mother', 'Mother'
        GUARDIAN = 'guardian', 'Guardian'
        OTHER = 'other', 'Other'
        UNCLE = 'uncle', 'Uncle'
        AUNT = 'aunt', 'Aunt'
        COUSIN = 'cousin', 'Cousin'
        SIBLING = 'sibling', 'Sibling'
        GRANDPARENT = 'grandparent', 'Grandparent'

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='parent_links',
    )
    parent = models.ForeignKey(
        'students.Parent',
        on_delete=models.CASCADE,
        related_name='student_links',
    )
    relationship = models.CharField(
        max_length=20,
        choices=RelationshipChoices.choices,
    )
    is_primary = models.BooleanField(
        default=False,
        help_text='Primary contact for this student. Only one parent may be primary.',
    )
    is_emergency_contact = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'parent'],
                name='unique_student_parent_link',
            ),
            models.UniqueConstraint(
                fields=['student'],
                condition=models.Q(is_primary=True),
                name='unique_primary_parent_per_student',
            ),
        ]

    def __str__(self):
        return f'{self.parent} ({self.get_relationship_display()}) → {self.student}'


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
    # Denormalized from stream for filtering/fees; always synced from stream on save.
    class_level = models.ForeignKey(
        'academics.ClassLevel',
        on_delete=models.PROTECT,
        related_name='enrollments',
    )
    stream = models.ForeignKey(
        'academics.ClassStream',
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

    def clean(self):
        super().clean()
        if self.stream_id:
            self.class_level_id = self.stream.class_level_id
        if (
            self.stream_id
            and self.class_level_id
            and self.stream.class_level_id != self.class_level_id
        ):
            raise ValidationError({
                'stream': 'Stream must belong to the selected class.',
            })

    def save(self, *args, **kwargs):
        if self.stream_id:
            self.class_level_id = self.stream.class_level_id
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.student} ({self.term})'
