from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from shared.models import BaseModel


class FeeStructure(BaseModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
        APPLIED = 'applied', 'Applied'
        CARRIED_FORWARD = 'carried_forward', 'Carried Forward'

    EDITABLE_STATUSES = frozenset({
        Status.DRAFT,
        Status.PUBLISHED,
        Status.CARRIED_FORWARD,
    })

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='fee_structures',
    )
    term = models.ForeignKey(
        'schools.Term',
        on_delete=models.CASCADE,
        related_name='fee_structures',
    )
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='created_fee_structures',
    )
    published_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'term'],
                name='unique_fee_structure_per_school_and_term',
            ),
        ]

    @property
    def is_locked(self):
        return self.status == self.Status.APPLIED

    @property
    def is_editable(self):
        return self.status in self.EDITABLE_STATUSES

    def clean(self):
        super().clean()
        if self.term_id and self.school_id and self.term.school_id != self.school_id:
            raise ValidationError({
                'term': 'Term must belong to the same school.',
            })

    def save(self, *args, **kwargs):
        if self.term_id:
            self.name = (
                f'{self.term.academic_year.academic_year} '
                f'{self.term.get_term_display()} Fees'
            )
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class FeeItem(BaseModel):
    class AppliesToType(models.TextChoices):
        LEVEL = 'level', 'Level'
        CLASS = 'class', 'Class'
        SCHOOL = 'school', 'School'

    class StudentType(models.TextChoices):
        NEW_STUDENT = 'new_student', 'New Student'
        CONTINUING_STUDENT = 'continuing_student', 'Continuing Student'
        ALL_STUDENTS = 'all_students', 'All Students'

    fee_structure = models.ForeignKey(
        FeeStructure,
        on_delete=models.CASCADE,
        related_name='fee_items',
    )
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, default='')
    applies_to_type = models.CharField(
        max_length=10,
        choices=AppliesToType.choices,
    )
    applies_to_id = models.UUIDField(null=True, blank=True)
    student_type = models.CharField(
        max_length=20,
        choices=StudentType.choices,
        default=StudentType.ALL_STUDENTS,
    )


    def clean(self):
        super().clean()
        errors = {}

        if self.fee_structure_id and self.fee_structure.is_locked:
            raise ValidationError('Fee items cannot be changed after the structure is applied.')

        if self.amount is not None and self.amount < 0:
            errors['amount'] = 'Amount must be zero or greater.'

        if self.applies_to_type == self.AppliesToType.SCHOOL:
            if self.applies_to_id:
                errors['applies_to_id'] = (
                    'School-wide fees must not specify an applies_to_id.'
                )
        elif not self.applies_to_id:
            errors['applies_to_id'] = (
                'Level and class fees must specify an applies_to_id.'
            )
        elif self.fee_structure_id:
            self._validate_applies_to_target(errors)

        if errors:
            raise ValidationError(errors)

    def _validate_applies_to_target(self, errors):
        from academics.models import ClassLevel, Level

        school = self.fee_structure.school
        if self.applies_to_type == self.AppliesToType.LEVEL:
            if not Level.objects.filter(id=self.applies_to_id, school=school).exists():
                errors['applies_to_id'] = 'Level not found for this school.'
        elif self.applies_to_type == self.AppliesToType.CLASS:
            if not ClassLevel.objects.filter(id=self.applies_to_id, school=school).exists():
                errors['applies_to_id'] = 'Class not found for this school.'

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class StudentFee(BaseModel):
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='student_fees',
    )
    term = models.ForeignKey(
        'schools.Term',
        on_delete=models.PROTECT,
        related_name='student_fees',
    )
    fee_structure = models.ForeignKey(
        FeeStructure,
        on_delete=models.PROTECT,
        related_name='student_fees',
    )
    fee_item = models.ForeignKey(
        FeeItem,
        on_delete=models.PROTECT,
        related_name='student_fees',
    )
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'fee_item'],
                name='unique_student_fee_per_fee_item',
            ),
        ]
        ordering = ['name']

    def clean(self):
        super().clean()
        if self.term_id and self.fee_structure_id and self.term_id != self.fee_structure.term_id:
            raise ValidationError({
                'term': 'Term must match the fee structure term.',
            })

    def save(self, *args, **kwargs):
        if self.fee_item_id and not self.name:
            self.name = self.fee_item.name
        if self.fee_structure_id and not self.term_id:
            self.term_id = self.fee_structure.term_id
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.student} - {self.name}'


class Payment(BaseModel):
    class PaymentMethod(models.TextChoices):
        CASH = 'cash', 'Cash'
        CHEQUE = 'cheque', 'Cheque'
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        MOBILE_MONEY = 'mobile_money', 'Mobile Money'
        ADVANCE_CREDIT = 'advance_credit', 'Advance Credit'
        OTHER = 'other', 'Other'

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='payments',
    )
    term = models.ForeignKey(
        'schools.Term',
        on_delete=models.PROTECT,
        related_name='payments',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    paid_at = models.DateTimeField(default=timezone.now)
    payment_reference = models.CharField(max_length=255, blank=True, default='')
    payment_notes = models.TextField(blank=True, default='')
    recorded_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='recorded_payments',
    )

    class Meta:
        ordering = ['-paid_at']

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({'amount': 'Payment amount must be greater than zero.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Receipt(BaseModel):
    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name='receipt',
    )
    receipt_number = models.CharField(max_length=50, unique=True)
    issued_at = models.DateTimeField(default=timezone.now)
    issued_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='issued_receipts',
    )

    class Meta:
        ordering = ['-issued_at']

    def __str__(self):
        return self.receipt_number


class StudentFeeCredit(BaseModel):
    """Advance/excess payment held for a student until applied to a later term."""

    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        APPLIED = 'applied', 'Applied'
        REFUNDED = 'refunded', 'Refunded'

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='fee_credits',
    )
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='fee_credits',
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Original advance amount created from an excess payment.',
    )
    remaining_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='How much of this advance is still unused.',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )
    source_payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name='created_credits',
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name='fee_credit_amount_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(remaining_amount__gte=0),
                name='fee_credit_remaining_non_negative',
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.amount is not None and self.amount <= 0:
            errors['amount'] = 'Amount must be greater than zero.'
        if self.remaining_amount is not None and self.remaining_amount < 0:
            errors['remaining_amount'] = 'Remaining amount cannot be negative.'
        if (
            self.amount is not None
            and self.remaining_amount is not None
            and self.remaining_amount > self.amount
        ):
            errors['remaining_amount'] = 'Remaining cannot exceed original amount.'
        if self.student_id and self.school_id and self.student.school_id != self.school_id:
            errors['school'] = 'School must match the student school.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.student_id and not self.school_id:
            self.school_id = self.student.school_id
        if self.remaining_amount is None and self.amount is not None:
            self.remaining_amount = self.amount
        if self.remaining_amount == 0 and self.status == self.Status.AVAILABLE:
            self.status = self.Status.APPLIED
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.student} credit {self.remaining_amount}/{self.amount}'
