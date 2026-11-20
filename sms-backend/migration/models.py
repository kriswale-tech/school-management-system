from django.conf import settings
from django.db import models
from django.db.models import Q

from shared.models import BaseModel


class MigrationJob(BaseModel):
    class JobType(models.TextChoices):
        STUDENT_ENROLLMENT = 'student_enrollment', 'Student and enrollment'
        FEE_FINANCIAL_HISTORY = 'fee_financial_history', 'Fee and financial history'

    class Template(models.TextChoices):
        STUDENT_INFORMATION = 'student_information', 'Student information'
        ENROLLMENT_HISTORY = 'enrollment_history', 'Enrollment history'
        OPENING_BALANCES = 'opening_balances', 'Opening balances'
        HISTORICAL_FINANCE = 'historical_finance', 'Fee history'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        UPLOADED = 'uploaded', 'Uploaded'
        MAPPING = 'mapping', 'Mapping'
        VALIDATING = 'validating', 'Validating'
        PREVIEW_READY = 'preview_ready', 'Preview ready'
        COMMITTING = 'committing', 'Committing'
        PARTIALLY_COMMITTED = 'partially_committed', 'Partially committed'
        COMMITTED = 'committed', 'Committed'
        FAILED = 'failed', 'Failed'
        ABANDONED = 'abandoned', 'Abandoned'
        CANCELLED = 'cancelled', 'Cancelled'

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='migration_jobs',
    )
    job_type = models.CharField(max_length=40, choices=JobType.choices)
    template = models.CharField(max_length=40, blank=True, default='')
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='migration_jobs_created',
    )
    committed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='migration_jobs_committed',
    )
    committed_at = models.DateTimeField(null=True, blank=True)
    source_system = models.CharField(max_length=120, blank=True, default='')
    file_hash = models.CharField(max_length=64, blank=True, default='')
    session_id = models.UUIDField(null=True, blank=True)
    summary = models.JSONField(default=dict, blank=True)
    heartbeat_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['school', 'status'], name='migration_job_school_status'),
            models.Index(fields=['school', 'job_type'], name='migration_job_school_type'),
        ]

    def __str__(self):
        return f'{self.get_job_type_display()} {self.status}'


class MappingProfile(BaseModel):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='migration_profiles',
    )
    name = models.CharField(max_length=120)
    source_system = models.CharField(max_length=120, blank=True, default='')
    job_type = models.CharField(max_length=40, choices=MigrationJob.JobType.choices)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='migration_profiles_created',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'job_type', 'name'],
                name='unique_migration_profile_name',
            ),
        ]
        ordering = ['name']

    def __str__(self):
        return self.name


class MigrationFile(BaseModel):
    class Status(models.TextChoices):
        STORED = 'stored', 'Stored'
        INSPECTING = 'inspecting', 'Inspecting'
        READY = 'ready', 'Ready'
        REJECTED = 'rejected', 'Rejected'

    job = models.ForeignKey(
        MigrationJob,
        on_delete=models.CASCADE,
        related_name='files',
    )
    original_filename = models.CharField(max_length=255)
    storage_key = models.CharField(max_length=500)
    file_hash = models.CharField(max_length=64)
    file_size = models.PositiveIntegerField()
    content_type = models.CharField(max_length=120, blank=True, default='')
    detected_encoding = models.CharField(max_length=40, blank=True, default='')
    detected_delimiter = models.CharField(max_length=8, blank=True, default='')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='migration_files_uploaded',
    )
    retention_until = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.STORED,
    )
    error = models.TextField(blank=True, default='')
    role = models.CharField(max_length=20, blank=True, default='')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['job', 'file_hash'],
                name='unique_migration_file_hash_per_job',
            ),
            models.UniqueConstraint(
                fields=['job', 'role'],
                condition=~Q(role=''),
                name='unique_migration_file_role',
            ),
        ]
        ordering = ['created_at']

    def __str__(self):
        return self.original_filename


class MigrationSheet(BaseModel):
    migration_file = models.ForeignKey(
        MigrationFile,
        on_delete=models.CASCADE,
        related_name='sheets',
    )
    sheet_name = models.CharField(max_length=200)
    header_row = models.PositiveIntegerField(default=1)
    detected_headers = models.JSONField(default=list, blank=True)
    sample_rows = models.JSONField(default=list, blank=True)
    row_count = models.PositiveIntegerField(default=0)
    included = models.BooleanField(default=True)
    mapping_profile = models.ForeignKey(
        MappingProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sheets',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['migration_file', 'sheet_name'],
                name='unique_migration_sheet_name',
            ),
        ]
        ordering = ['created_at']

    def __str__(self):
        return self.sheet_name


class FieldMapping(BaseModel):
    profile = models.ForeignKey(
        MappingProfile,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='field_mappings',
    )
    sheet = models.ForeignKey(
        MigrationSheet,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='field_mappings',
    )
    source_column = models.CharField(max_length=255)
    target_field = models.CharField(max_length=64, blank=True, default='')
    ignored = models.BooleanField(default=False)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(profile__isnull=False) | Q(sheet__isnull=False),
                name='field_mapping_has_owner',
            ),
        ]
        ordering = ['position', 'source_column']

    def __str__(self):
        return f'{self.source_column} → {self.target_field or "ignored"}'


class MigrationTransform(BaseModel):
    class Step(models.TextChoices):
        TRIM = 'trim', 'Trim'
        SPLIT_NAME = 'split_name', 'Split full name'
        COMBINE = 'combine', 'Combine fields'
        DATE = 'date', 'Parse date'
        PHONE = 'phone', 'Normalize phone'
        VALUE_MAP = 'value_map', 'Map values'

    field_mapping = models.ForeignKey(
        FieldMapping,
        on_delete=models.CASCADE,
        related_name='transforms',
    )
    step = models.CharField(max_length=32, choices=Step.choices)
    config = models.JSONField(default=dict, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['position', 'created_at']


class MigrationRow(BaseModel):
    class ValidationStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        READY = 'ready', 'Ready'
        BLOCKED = 'blocked', 'Blocked'

    class CommitStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SKIPPED = 'skipped', 'Skipped'
        COMMITTED = 'committed', 'Committed'
        FAILED = 'failed', 'Failed'
        ABANDONED = 'abandoned', 'Abandoned'

    job = models.ForeignKey(
        MigrationJob,
        on_delete=models.CASCADE,
        related_name='rows',
    )
    sheet = models.ForeignKey(
        MigrationSheet,
        on_delete=models.CASCADE,
        related_name='rows',
    )
    source_row_number = models.PositiveIntegerField()
    raw_values = models.JSONField(default=dict, blank=True)
    transformed_values = models.JSONField(default=dict, blank=True)
    validation_status = models.CharField(
        max_length=20,
        choices=ValidationStatus.choices,
        default=ValidationStatus.PENDING,
    )
    commit_status = models.CharField(
        max_length=20,
        choices=CommitStatus.choices,
        default=CommitStatus.PENDING,
    )
    errors = models.JSONField(default=list, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    proposal = models.JSONField(default=dict, blank=True)
    committed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['sheet', 'source_row_number'],
                name='unique_migration_source_row',
            ),
        ]
        indexes = [
            models.Index(
                fields=['job', 'validation_status'],
                name='migration_row_validation',
            ),
            models.Index(
                fields=['job', 'commit_status'],
                name='migration_row_commit',
            ),
        ]
        ordering = ['source_row_number']


class MigrationCommitRecord(BaseModel):
    """Idempotency key for a later operational commit. Phase 1 does not write one."""

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='migration_commit_records',
    )
    job_type = models.CharField(max_length=40, choices=MigrationJob.JobType.choices)
    file_hash = models.CharField(max_length=64)
    sheet_name = models.CharField(max_length=200)
    source_row_number = models.PositiveIntegerField()
    job = models.ForeignKey(
        MigrationJob,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commit_records',
    )
    source_transaction_id = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'school',
                    'job_type',
                    'file_hash',
                    'sheet_name',
                    'source_row_number',
                ],
                name='unique_migration_source_row_commit',
            ),
            models.UniqueConstraint(
                fields=['school', 'source_transaction_id'],
                condition=~Q(source_transaction_id=''),
                name='unique_migration_source_transaction',
            ),
        ]


class MigrationAuditEvent(BaseModel):
    class Action(models.TextChoices):
        UPLOAD = 'upload', 'Upload'
        INSPECT = 'inspect', 'Inspect'
        MAPPING = 'mapping', 'Mapping'
        VALIDATE = 'validate', 'Validate'
        PREVIEW = 'preview', 'Preview'
        DOWNLOAD = 'download', 'Download'
        MATCH = 'match', 'Match'
        COMMIT = 'commit', 'Commit'

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='migration_audit_events',
    )
    job = models.ForeignKey(
        MigrationJob,
        on_delete=models.CASCADE,
        related_name='audit_events',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='migration_audit_events',
    )
    action = models.CharField(max_length=32, choices=Action.choices)
    summary = models.CharField(max_length=500)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['school', 'job'], name='migration_audit_school_job'),
        ]


class ExternalStudentReference(BaseModel):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='external_student_references',
    )
    source_system = models.CharField(max_length=120, blank=True, default='')
    external_id = models.CharField(max_length=255)
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        related_name='external_references',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'source_system', 'external_id'],
                name='unique_external_student_reference',
            ),
        ]


class MigrationMatchDecision(BaseModel):
    class Kind(models.TextChoices):
        EXACT = 'exact', 'Exact'
        PROBABLE = 'probable', 'Probable'
        AMBIGUOUS = 'ambiguous', 'Ambiguous'
        NONE = 'none', 'No match'

    class Decision(models.TextChoices):
        PENDING = 'pending', 'Pending'
        LINK = 'link', 'Link'
        CREATE = 'create', 'Create'

    row = models.OneToOneField(
        MigrationRow,
        on_delete=models.CASCADE,
        related_name='match_decision',
    )
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.NONE)
    decision = models.CharField(max_length=20, choices=Decision.choices, default=Decision.PENDING)
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='migration_match_decisions',
    )
    reason = models.CharField(max_length=255, blank=True, default='')
    candidates = models.JSONField(default=list, blank=True)
    field_resolution = models.JSONField(default=dict, blank=True)
    guardian_decision = models.CharField(max_length=32, blank=True, default='')
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='migration_match_decisions',
    )


class ClassValueResolution(BaseModel):
    """One confirmed class choice, applied to every row with the same source value."""

    job = models.ForeignKey(
        MigrationJob,
        on_delete=models.CASCADE,
        related_name='class_resolutions',
    )
    source_value = models.CharField(max_length=255)
    stream = models.ForeignKey(
        'academics.ClassStream',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='migration_class_resolutions',
    )
    use_snapshot = models.BooleanField(default=False)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='migration_class_resolutions',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['job', 'source_value'],
                name='unique_migration_class_source_value',
            ),
        ]


class SchoolValueMapping(BaseModel):
    """Approved source value for one school. Never shared with another school."""

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='migration_value_mappings',
    )
    field_name = models.CharField(max_length=64)
    source_value = models.CharField(max_length=255)
    source_label = models.CharField(max_length=255, blank=True, default='')
    canonical_value = models.CharField(max_length=255, blank=True, default='')
    stream = models.ForeignKey(
        'academics.ClassStream',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='migration_value_mappings',
    )
    origin = models.CharField(max_length=32, blank=True, default='manual')
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='migration_value_mappings',
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'field_name', 'source_value'],
                name='unique_school_migration_value',
            ),
        ]


class MigrationOpeningBalance(BaseModel):
    """One imported outstanding balance. The ledger charge is the linked StudentFee."""

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='migration_opening_balances',
    )
    job = models.ForeignKey(
        MigrationJob,
        on_delete=models.PROTECT,
        related_name='opening_balances',
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        related_name='migration_opening_balances',
    )
    term = models.ForeignKey(
        'schools.Term',
        on_delete=models.PROTECT,
        related_name='migration_opening_balances',
    )
    student_fee = models.OneToOneField(
        'fees.StudentFee',
        on_delete=models.PROTECT,
        related_name='migration_opening_balance',
    )
    file_hash = models.CharField(max_length=64, blank=True, default='')
    sheet_name = models.CharField(max_length=255, blank=True, default='')
    source_row_number = models.PositiveIntegerField()
    source_reference = models.CharField(max_length=255, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='migration_opening_balances',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'student', 'term'],
                name='unique_opening_balance_per_student_term',
            ),
        ]


class MigrationHistoricalCharge(BaseModel):
    """One imported fee line. The ledger charge is the linked StudentFee."""

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='migration_historical_charges',
    )
    job = models.ForeignKey(
        MigrationJob,
        on_delete=models.PROTECT,
        related_name='historical_charges',
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        related_name='migration_historical_charges',
    )
    term = models.ForeignKey(
        'schools.Term',
        on_delete=models.PROTECT,
        related_name='migration_historical_charges',
    )
    student_fee = models.OneToOneField(
        'fees.StudentFee',
        on_delete=models.PROTECT,
        related_name='migration_historical_charge',
    )
    fee_name = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=64, blank=True, default='')
    sheet_name = models.CharField(max_length=255, blank=True, default='')
    source_row_number = models.PositiveIntegerField()
    source_reference = models.CharField(max_length=255, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='migration_historical_charges',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'student', 'term', 'fee_name'],
                name='unique_historical_charge_per_student_term_fee',
            ),
        ]


class MigrationHistoricalPayment(BaseModel):
    """One imported payment. Term shares are PaymentAllocation rows."""

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='migration_historical_payments',
    )
    job = models.ForeignKey(
        MigrationJob,
        on_delete=models.PROTECT,
        related_name='historical_payments',
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        related_name='migration_historical_payments',
    )
    payment = models.OneToOneField(
        'fees.Payment',
        on_delete=models.PROTECT,
        related_name='migration_historical_payment',
    )
    reference_key = models.CharField(max_length=255)
    legacy_receipt_number = models.CharField(max_length=255, blank=True, default='')
    payment_type = models.CharField(max_length=20)
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='migration_historical_payments',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'reference_key'],
                name='unique_historical_payment_reference',
            ),
        ]
