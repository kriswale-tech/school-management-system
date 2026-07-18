from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from fees.models import FeeItem, FeeStructure, Payment, StudentFee
from schools.models import Term


def _previous_term(term):
    terms = list(
        Term.objects.filter(
            academic_year=term.academic_year,
            school=term.school,
        ).order_by('start_date'),
    )
    index = next((idx for idx, item in enumerate(terms) if item.id == term.id), None)
    if index is None or index == 0:
        return None
    return terms[index - 1]


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
        for fee_item in fee_items:
            if not _student_matches_fee_item(enrollment, fee_item):
                continue
            student_fees.append(
                StudentFee(
                    student=enrollment.student,
                    term=fee_structure.term,
                    fee_structure=fee_structure,
                    fee_item=fee_item,
                    name=fee_item.name,
                    amount=fee_item.amount,
                ),
            )

    StudentFee.objects.bulk_create(student_fees, ignore_conflicts=True)

    fee_structure.status = FeeStructure.Status.APPLIED
    fee_structure.applied_at = timezone.now()
    fee_structure.save(update_fields=['status', 'applied_at', 'updated_at'])
    return fee_structure


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
