from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from fees.models import FeeItem, FeeStructure, Payment, StudentFee
from schools.models import Term


def _previous_term(term):
    return (
        Term.objects.filter(
            school=term.school,
            start_date__lt=term.start_date,
        )
        .order_by('-start_date')
        .first()
    )


def _student_matches_fee_item(enrollment, fee_item):
    if fee_item.student_type == FeeItem.StudentType.NEW_STUDENT and not enrollment.is_new_student:
        return False
    if fee_item.student_type == FeeItem.StudentType.CONTINUING_STUDENT and enrollment.is_new_student:
        return False

    if fee_item.applies_to_type == FeeItem.AppliesToType.SCHOOL:
        return True
    if fee_item.applies_to_type == FeeItem.AppliesToType.LEVEL:
        return enrollment.class_level.level_id == fee_item.applies_to_id
    if fee_item.applies_to_type == FeeItem.AppliesToType.CLASS:
        return enrollment.class_level_id == fee_item.applies_to_id
    return False


@transaction.atomic
def carry_forward_fee_structure(*, school, term, created_by):
    """Create a draft structure for a term by copying the previous term's items."""
    existing = FeeStructure.objects.filter(school=school, term=term).first()
    if existing:
        return existing

    previous_term = _previous_term(term)
    if previous_term is None:
        raise ValidationError({
            'term': 'No previous term exists to carry fees forward from.',
        })

    source = (
        FeeStructure.objects.filter(school=school, term=previous_term)
        .prefetch_related('fee_items')
        .first()
    )
    if source is None:
        raise ValidationError({
            'term': 'Previous term has no fee structure to carry forward.',
        })

    structure = FeeStructure.objects.create(
        school=school,
        term=term,
        status=FeeStructure.Status.CARRIED_FORWARD,
        created_by=created_by,
    )
    FeeItem.objects.bulk_create([
        FeeItem(
            fee_structure=structure,
            name=item.name,
            amount=item.amount,
            description=item.description,
            applies_to_type=item.applies_to_type,
            applies_to_id=item.applies_to_id,
            student_type=item.student_type,
        )
        for item in source.fee_items.all()
    ])
    return structure


def get_or_create_fee_structure(*, school, term, created_by):
    structure = FeeStructure.objects.filter(school=school, term=term).first()
    if structure:
        return structure

    previous_term = _previous_term(term)
    if previous_term and FeeStructure.objects.filter(school=school, term=previous_term).exists():
        return carry_forward_fee_structure(
            school=school,
            term=term,
            created_by=created_by,
        )

    return FeeStructure.objects.create(
        school=school,
        term=term,
        created_by=created_by,
    )


@transaction.atomic
def publish_fee_structure(fee_structure):
    if fee_structure.is_locked:
        raise ValidationError('Applied fee structures cannot be published again.')
    if not fee_structure.fee_items.exists():
        raise ValidationError('Add at least one fee item before publishing.')

    fee_structure.status = FeeStructure.Status.PUBLISHED
    fee_structure.published_at = timezone.now()
    fee_structure.save(update_fields=['status', 'published_at', 'updated_at'])
    return fee_structure


def _student_fee_rows_for_enrollment(enrollment, fee_structure, fee_items):
    rows = []
    for fee_item in fee_items:
        if not _student_matches_fee_item(enrollment, fee_item):
            continue
        rows.append(
            StudentFee(
                student=enrollment.student,
                term=fee_structure.term,
                fee_structure=fee_structure,
                fee_item=fee_item,
                name=fee_item.name,
                amount=fee_item.amount,
            ),
        )
    return rows


@transaction.atomic
def apply_fee_structure(fee_structure):
    if fee_structure.is_locked:
        raise ValidationError('This fee structure has already been applied.')

    if fee_structure.status not in {
        FeeStructure.Status.PUBLISHED,
        FeeStructure.Status.CARRIED_FORWARD,
    }:
        raise ValidationError('Publish the fee structure before applying.')

    if not fee_structure.fee_items.exists():
        raise ValidationError('Add at least one fee item before applying.')

    from students.models import ClassEnrollment

    enrollments = ClassEnrollment.objects.filter(
        term=fee_structure.term,
        student__school=fee_structure.school,
    ).select_related('student', 'class_level', 'class_level__level')

    fee_items = list(fee_structure.fee_items.all())
    student_fees = []
    for enrollment in enrollments:
        student_fees.extend(
            _student_fee_rows_for_enrollment(enrollment, fee_structure, fee_items),
        )

    StudentFee.objects.bulk_create(student_fees, ignore_conflicts=True)

    from fees.services.credits import apply_available_credits_for_term

    apply_available_credits_for_term(
        school=fee_structure.school,
        term=fee_structure.term,
        recorded_by=fee_structure.created_by,
    )

    fee_structure.status = FeeStructure.Status.APPLIED
    fee_structure.applied_at = timezone.now()
    fee_structure.save(update_fields=['status', 'applied_at', 'updated_at'])
    return fee_structure


@transaction.atomic
def ensure_enrollment_fees(enrollment):
    """
    Stamp matching StudentFee rows for a newly enrolled student when that
    term's fee structure is already applied. No-op if the catalog is not live.
    """
    from students.models import ClassEnrollment

    enrollment = (
        ClassEnrollment.objects.select_related(
            'student',
            'term',
            'class_level',
            'class_level__level',
        ).get(pk=enrollment.pk)
    )
    fee_structure = (
        FeeStructure.objects.filter(
            school=enrollment.student.school,
            term=enrollment.term,
            status=FeeStructure.Status.APPLIED,
        )
        .prefetch_related('fee_items')
        .first()
    )
    if fee_structure is None:
        return []

    fee_items = list(fee_structure.fee_items.all())
    rows = _student_fee_rows_for_enrollment(enrollment, fee_structure, fee_items)
    if not rows:
        return []

    StudentFee.objects.bulk_create(rows, ignore_conflicts=True)

    from fees.services.credits import apply_available_credits_for_student

    apply_available_credits_for_student(
        student=enrollment.student,
        term=enrollment.term,
        recorded_by=fee_structure.created_by,
        school=fee_structure.school,
    )
    return rows


def get_student_term_balance(*, student, term):
    fees = list(
        StudentFee.objects.filter(student=student, term=term).order_by('name'),
    )
    payments = list(
        Payment.objects.filter(student=student, term=term).order_by('-paid_at'),
    )

    total_billed = sum((fee.amount for fee in fees), Decimal('0.00'))
    total_paid = sum((payment.amount for payment in payments), Decimal('0.00'))
    balance = total_billed - total_paid

    if balance <= 0 and total_billed > 0:
        payment_status = 'fully_paid'
    elif total_paid > 0:
        payment_status = 'partially_paid'
    elif total_billed > 0:
        payment_status = 'owing'
    else:
        payment_status = 'no_fees'

    return {
        'student_id': student.id,
        'term_id': term.id,
        'total_billed': total_billed,
        'total_paid': total_paid,
        'balance': balance,
        'payment_status': payment_status,
        'fee_items': [
            {
                'id': fee.id,
                'name': fee.name,
                'amount': fee.amount,
                'fee_item_id': fee.fee_item_id,
            }
            for fee in fees
        ],
        'payments': [
            {
                'id': payment.id,
                'amount': payment.amount,
                'payment_method': payment.payment_method,
                'paid_at': payment.paid_at,
                'payment_reference': payment.payment_reference,
            }
            for payment in payments
        ],
    }


def validate_fee_structure_ready(fee_structure):
    fee_structure.full_clean()
    if not fee_structure.fee_items.exists():
        raise ValidationError('Fee structure must contain at least one fee item.')


def _aggregate_payment_status(*, total_billed, total_paid):
    balance = total_billed - total_paid
    if balance <= 0 and total_billed > 0:
        return 'fully_paid'
    if total_paid > 0:
        return 'partially_paid'
    if total_billed > 0:
        return 'owing'
    return 'no_fees'


def build_student_term_fees(*, student, term):
    """Term fee breakdown for API responses (no payment ledger)."""
    balance = get_student_term_balance(student=student, term=term)
    return {
        'term_id': term.id,
        'term': term.term,
        'term_name': term.get_term_display(),
        'total_billed': balance['total_billed'],
        'total_paid': balance['total_paid'],
        'balance': balance['balance'],
        'payment_status': balance['payment_status'],
        'fee_items': [
            {
                'id': item['id'],
                'name': item['name'],
                'amount': item['amount'],
            }
            for item in balance['fee_items']
        ],
    }


def get_student_academic_year_fees(*, student, academic_year):
    """Aggregate billed/paid totals and per-term breakdown for one academic year."""
    terms = list(
        Term.objects.filter(
            school=student.school,
            academic_year=academic_year,
        ).order_by('-start_date'),
    )
    term_blocks = [build_student_term_fees(student=student, term=term) for term in terms]

    total_billed = sum((block['total_billed'] for block in term_blocks), Decimal('0.00'))
    total_paid = sum((block['total_paid'] for block in term_blocks), Decimal('0.00'))
    balance = total_billed - total_paid

    return {
        'student_id': student.id,
        'academic_year_id': academic_year.id,
        'academic_year': academic_year.academic_year,
        'total_billed': total_billed,
        'total_paid': total_paid,
        'balance': balance,
        'payment_status': _aggregate_payment_status(
            total_billed=total_billed,
            total_paid=total_paid,
        ),
        'terms': term_blocks,
    }


def get_student_current_year_fees(*, school, student):
    """Fees for the school's active academic year (via active term)."""
    from students.services import get_active_term

    active_term = get_active_term(
        school,
        detail='Set an active term before viewing student fees.',
    )
    return get_student_academic_year_fees(
        student=student,
        academic_year=active_term.academic_year,
    )


def get_student_fees(*, school, student, academic_year_id=None, term_id=None):
    """
    Fee breakdown for a student, optionally scoped to an academic year and/or term.
    Defaults to the active academic year when neither filter is provided.
    """
    from rest_framework.exceptions import ValidationError
    from schools.models import AcademicYear
    from students.services import get_active_term, resolve_term

    if term_id:
        term = resolve_term(school, term_id)
        year_fees = get_student_academic_year_fees(
            student=student,
            academic_year=term.academic_year,
        )
        term_blocks = [block for block in year_fees['terms'] if block['term_id'] == term.id]
        total_billed = sum((block['total_billed'] for block in term_blocks), Decimal('0.00'))
        total_paid = sum((block['total_paid'] for block in term_blocks), Decimal('0.00'))
        return {
            **year_fees,
            'total_billed': total_billed,
            'total_paid': total_paid,
            'balance': total_billed - total_paid,
            'payment_status': _aggregate_payment_status(
                total_billed=total_billed,
                total_paid=total_paid,
            ),
            'terms': term_blocks,
        }

    if academic_year_id:
        academic_year = AcademicYear.objects.filter(school=school, id=academic_year_id).first()
        if academic_year is None:
            raise ValidationError({'academic_year': 'Academic year not found in this school.'})
        return get_student_academic_year_fees(student=student, academic_year=academic_year)

    return get_student_current_year_fees(school=school, student=student)


def list_student_payments(*, school, student, academic_year_id=None, term_id=None):
    """Payment ledger rows for a student, optionally filtered by year or term."""
    from rest_framework.exceptions import ValidationError
    from fees.models import Receipt
    from schools.models import AcademicYear

    queryset = (
        Payment.objects.filter(student=student, term__school=school)
        .select_related('term', 'term__academic_year', 'receipt')
        .order_by('-paid_at')
    )

    if term_id:
        queryset = queryset.filter(term_id=term_id)
    elif academic_year_id:
        academic_year = AcademicYear.objects.filter(school=school, id=academic_year_id).first()
        if academic_year is None:
            raise ValidationError({'academic_year': 'Academic year not found in this school.'})
        queryset = queryset.filter(term__academic_year=academic_year)

    rows = []
    for payment in queryset:
        try:
            receipt = payment.receipt
        except Receipt.DoesNotExist:
            receipt = None
        rows.append({
            'id': payment.id,
            'term_id': payment.term_id,
            'term': payment.term.term,
            'term_name': payment.term.get_term_display(),
            'academic_year_id': payment.term.academic_year_id,
            'academic_year': payment.term.academic_year.academic_year,
            'amount': payment.amount,
            'payment_method': payment.payment_method,
            'payment_method_display': payment.get_payment_method_display(),
            'paid_at': payment.paid_at,
            'payment_reference': payment.payment_reference,
            'receipt': (
                {
                    'id': receipt.id,
                    'receipt_number': receipt.receipt_number,
                }
                if receipt is not None
                else None
            ),
        })
    return rows


def get_student_fee_history(*, school, student, academic_year_id=None):
    """
    Academic years that have StudentFee or Payment data for this student.
    Optional academic_year_id filters to a single year (must have data).
    """
    from schools.models import AcademicYear
    from rest_framework.exceptions import NotFound, ValidationError

    fee_year_ids = StudentFee.objects.filter(
        student=student,
        term__school=school,
    ).values_list('term__academic_year_id', flat=True)
    payment_year_ids = Payment.objects.filter(
        student=student,
        term__school=school,
    ).values_list('term__academic_year_id', flat=True)
    year_ids = set(fee_year_ids) | set(payment_year_ids)

    if academic_year_id:
        academic_year = AcademicYear.objects.filter(
            school=school,
            id=academic_year_id,
        ).first()
        if academic_year is None:
            raise ValidationError({'academic_year': 'Academic year not found in this school.'})
        if academic_year.id not in year_ids:
            raise NotFound({'detail': 'No fee history for this student in that academic year.'})
        years_qs = [academic_year]
    else:
        years_qs = list(
            AcademicYear.objects.filter(school=school, id__in=year_ids).order_by('-start_date'),
        )

    years = [
        get_student_academic_year_fees(student=student, academic_year=year)
        for year in years_qs
    ]

    return {
        'student_id': student.id,
        'years': years,
    }
