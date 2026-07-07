from django.conf import settings
from django.db import models

from shared.models import BaseModel

# Create your models here.
class School(BaseModel):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, null=True, blank=True)
    gps_address = models.CharField(max_length=15, null=True, blank=True)
    box_address = models.CharField(max_length=15, null=True, blank=True)
    phone_number = models.CharField(max_length=15)
    phone_number_alt = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    logo = models.ImageField(upload_to=f'{settings.PARENT_CLOUDINARY_FOLDER}/school-logos/', null=True, blank=True)
    motto = models.TextField(null=True, blank=True)

    setup_completed = models.BooleanField(default=False)
    setup_completed_at = models.DateTimeField(null=True, blank=True)
    provisioned_curriculum = models.ForeignKey(
        'academics.Curriculum',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='schools',
    )


class SchoolSetup(models.Model):
    class SetupStep(models.TextChoices):
        SCHOOL_PROFILE = 'school_profile', 'School profile'
        ACADEMIC_YEAR_TERM = 'academic_year_term', 'Academic year & term'
        CLASSES_AND_SUBJECTS = 'classes_and_subjects', 'Classes & subjects'
        ASSESSMENT = 'assessment', 'Assessment'
        FEES = 'fees', 'Fees'
        TEACHERS = 'teachers', 'Add Teachers'
        STAFF = 'staff', 'Add Staff'
        COMPLETED = 'completed', 'Completed'

    school = models.OneToOneField(
        'School',
        on_delete=models.CASCADE,
        related_name='setup',
    )
    current_step = models.CharField(
        max_length=50,
        choices=SetupStep.choices,
        default=SetupStep.SCHOOL_PROFILE,
    )
    completed_steps = models.JSONField(default=list)
    progress_percentage = models.PositiveSmallIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class AcademicYear(BaseModel):
    school = models.ForeignKey(
        'School',
        on_delete=models.CASCADE,
        related_name='academic_years',
    )
    academic_year = models.CharField(max_length=9)  # e.g. 2026/2027
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['school'],
                condition=models.Q(is_active=True),
                name='unique_active_academic_year_per_school',
            ),
            models.UniqueConstraint(
                fields=['school', 'academic_year'],
                name='unique_academic_year_label_per_school',
            ),
        ]

    def __str__(self):
        return f'{self.academic_year} ({self.school.name})'


class Term(BaseModel):
    class TermChoices(models.TextChoices):
        FIRST_TERM = 'first_term', 'First Term'
        SECOND_TERM = 'second_term', 'Second Term'
        THIRD_TERM = 'third_term', 'Third Term'

    school = models.ForeignKey(
        'School',
        on_delete=models.CASCADE,
        related_name='terms',
    )
    academic_year = models.ForeignKey(
        'AcademicYear',
        on_delete=models.CASCADE,
        related_name='terms',
    )
    term = models.CharField(
        max_length=15,
        choices=TermChoices.choices,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)

    class Meta:
        ordering = ['start_date']
        constraints = [
            models.UniqueConstraint(
                fields=['school'],
                condition=models.Q(is_active=True),
                name='unique_active_term_per_school',
            ),
            models.UniqueConstraint(
                fields=['academic_year', 'term'],
                name='unique_term_per_academic_year',
            ),
        ]

    def __str__(self):
        return f'{self.get_term_display()} ({self.academic_year.academic_year})'