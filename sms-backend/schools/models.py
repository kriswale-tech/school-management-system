from django.db import models
from shared.models import BaseModel
from django.conf import settings

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
    pass


class Term(BaseModel):
    pass

class Level(BaseModel):
    pass

class Class(BaseModel):
    pass