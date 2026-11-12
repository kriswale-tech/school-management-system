from decimal import Decimal

from django.conf import settings
from django.db import models

from shared.models import BaseModel

# Create your models here.
class School(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACTIVE = 'active', 'Active'
        SUSPENDED = 'suspended', 'Suspended'
        ARCHIVED = 'archived', 'Archived'

    class Category(models.TextChoices):
        CRECHE = 'creche', 'Creche'
        NURSERY = 'nursery', 'Nursery'
        KINDERGARTEN = 'kindergarten', 'Kindergarten'
        PRIMARY = 'primary', 'Primary'
        JHS = 'jhs', 'Junior High School'
        SHS = 'shs', 'Senior High School'
        MIXED = 'mixed', 'Mixed levels'
        OTHER = 'other', 'Other'

    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, null=True, blank=True)
    gps_address = models.CharField(max_length=15, null=True, blank=True)
    box_address = models.CharField(max_length=15, null=True, blank=True)
    phone_number = models.CharField(max_length=15)
    phone_number_alt = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    logo = models.ImageField(upload_to=f'{settings.PARENT_CLOUDINARY_FOLDER}/school-logos/', null=True, blank=True)
    motto = models.TextField(null=True, blank=True)
    student_id_prefix = models.CharField(
        max_length=12,
        blank=True,
        default='',
        help_text='Used for new student IDs. Blank keeps a prefix from the school name.',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    region = models.CharField(max_length=100, blank=True, default='')
    category = models.CharField(
        max_length=32,
        choices=Category.choices,
        blank=True,
        default='',
    )
    activated_at = models.DateTimeField(null=True, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)

    setup_completed = models.BooleanField(default=False)
    setup_completed_at = models.DateTimeField(null=True, blank=True)
    provisioned_curriculum = models.ForeignKey(
        'academics.Curriculum',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='schools',
    )
    accepted_curriculum = models.ForeignKey(
        'academics.Curriculum',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='schools_accepting',
        help_text='Version the school has accepted. It is applied when the next term starts.',
    )

    @property
    def is_accessible(self) -> bool:
        """Members may use the school app when pending (setup) or active."""
        return self.status in {self.Status.PENDING, self.Status.ACTIVE}


class SchoolSetup(models.Model):
    class SetupStep(models.TextChoices):
        SCHOOL_PROFILE = 'school_profile', 'School profile'
        ACADEMIC_YEAR_TERM = 'academic_year_term', 'Academic year & term'
        CLASSES_AND_SUBJECTS = 'classes_and_subjects', 'Classes & subjects'
        ASSESSMENT = 'assessment', 'Assessment'
        FEES = 'fees', 'Fees'
        TEACHERS = 'teachers', 'Add Teachers'
        STAFF = 'staff', 'Add Staff'  # Optional; setup can be finalized without it.
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


class SchoolSettings(BaseModel):
    """In-app alert rules, report-card fields, and guardian outreach for one school."""

    class GuardianAudience(models.TextChoices):
        PRIMARY = 'primary', 'Primary guardian only'
        ALL = 'all', 'All guardians'

    class ReportParentNotifyMode(models.TextChoices):
        MANUAL = 'manual', 'Staff triggered'
        AUTO = 'auto', 'Automatic on release'

    class GuardianChannel(models.TextChoices):
        SMS = 'sms', 'SMS'
        EMAIL = 'email', 'Email'
        BOTH = 'both', 'SMS and email'

    class DebtReminderFrequency(models.TextChoices):
        END_OF_MONTH = 'end_of_month', 'End of each month'
        WEEKLY = 'weekly', 'Weekly (Mondays)'
        BIWEEKLY = 'biweekly', 'Every 2 weeks (Mondays)'

    school = models.OneToOneField(
        'School',
        on_delete=models.CASCADE,
        related_name='school_settings',
    )
    fees_alert_enabled = models.BooleanField(default=True)
    fees_alert_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('1.00'),
        help_text='Alert when a student owes at least this amount on the active term.',
    )
    results_alert_enabled = models.BooleanField(default=True)
    enrollments_alert_enabled = models.BooleanField(default=True)
    guardians_alert_enabled = models.BooleanField(
        default=True,
        help_text='Alert admins and staff when enrolled students have no linked guardian.',
    )
    transition_popup_enabled = models.BooleanField(
        default=True,
        help_text='Show a popup on the dashboard while opening the next term still needs action.',
    )
    curriculum_alert_enabled = models.BooleanField(
        default=True,
        help_text='Show the curriculum update on the bell and the admin dashboard.',
    )
    report_show_logo = models.BooleanField(default=True)
    report_show_address = models.BooleanField(default=True)
    report_show_phones = models.BooleanField(default=True)
    report_show_email = models.BooleanField(default=True)

    guardian_audience = models.CharField(
        max_length=10,
        choices=GuardianAudience.choices,
        default=GuardianAudience.PRIMARY,
        help_text='Which linked guardians receive parent messages by default.',
    )
    report_parent_notify_mode = models.CharField(
        max_length=10,
        choices=ReportParentNotifyMode.choices,
        default=ReportParentNotifyMode.MANUAL,
        help_text='Whether report-ready messages go out automatically or only when staff send them.',
    )
    guardian_ward_enrolled_enabled = models.BooleanField(
        default=True,
        help_text='Notify guardians when a ward is added to the school.',
    )
    guardian_ward_enrolled_channels = models.CharField(
        max_length=10,
        choices=GuardianChannel.choices,
        default=GuardianChannel.BOTH,
    )
    guardian_payment_receipt_enabled = models.BooleanField(
        default=False,
        help_text='Placeholder: payment + receipt link to guardians (not wired yet).',
    )
    guardian_payment_receipt_channels = models.CharField(
        max_length=10,
        choices=GuardianChannel.choices,
        default=GuardianChannel.BOTH,
    )
    guardian_debt_reminder_enabled = models.BooleanField(
        default=False,
        help_text='Allow debt reminders to guardians (manual Fees desk and optional automation).',
    )
    guardian_debt_reminder_channels = models.CharField(
        max_length=10,
        choices=GuardianChannel.choices,
        default=GuardianChannel.BOTH,
    )
    guardian_debt_reminder_auto_enabled = models.BooleanField(
        default=False,
        help_text='Automatically remind guardians of outstanding balances on a schedule.',
    )
    guardian_debt_reminder_frequency = models.CharField(
        max_length=20,
        choices=DebtReminderFrequency.choices,
        default=DebtReminderFrequency.END_OF_MONTH,
        help_text='How often automatic debt reminders are sent (default: end of each month).',
    )
    guardian_report_ready_enabled = models.BooleanField(
        default=False,
        help_text='Placeholder: report download link to guardians (not wired yet).',
    )
    guardian_report_ready_channels = models.CharField(
        max_length=10,
        choices=GuardianChannel.choices,
        default=GuardianChannel.BOTH,
    )
    guardian_next_term_fees_enabled = models.BooleanField(
        default=False,
        help_text='Placeholder: next-term fees notice to guardians (not wired yet).',
    )
    guardian_next_term_fees_channels = models.CharField(
        max_length=10,
        choices=GuardianChannel.choices,
        default=GuardianChannel.BOTH,
    )

    def __str__(self):
        return f'Settings for {self.school.name}'