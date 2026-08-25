from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from fees.models import Payment, StudentFeeCredit


def get_student_advance_balance(*, student) -> Decimal:
    total = (
        StudentFeeCredit.objects.filter(
            student=student,
            status=StudentFeeCredit.Status.AVAILABLE,
        ).aggregate(
            total=Coalesce(Sum('remaining_amount'), Decimal('0.00')),
        )['total']
    )
    return total or Decimal('0.00')


def create_credit_from_excess(*, school, student, amount, source_payment):
    """Store leftover payment amount as available advance credit."""
    if amount is None or amount <= 0:
        return None

    return StudentFeeCredit.objects.create(
        student=student,
        school=school,
        amount=amount,
        remaining_amount=amount,
        status=StudentFeeCredit.Status.AVAILABLE,
        source_payment=source_payment,
        notes='Excess payment held as advance.',
    )


@transaction.atomic
def apply_available_credits_for_student(*, student, term, recorded_by, school=None):
    """Apply available advances to one student's billed balance for a term (FIFO)."""
    from fees.services.fees import get_student_term_balance

    school = school or student.school
    credits = list(
        StudentFeeCredit.objects.select_for_update()
        .filter(
            student=student,
            school=school,
            status=StudentFeeCredit.Status.AVAILABLE,
            remaining_amount__gt=0,
        )
        .order_by('created_at'),
    )
    if not credits:
        return []

    owing = get_student_term_balance(student=student, term=term)['balance']
    if owing <= 0:
        return []

    applied_payments = []
    remaining_to_cover = owing
    for credit in credits:
        if remaining_to_cover <= 0:
            break

        apply_amount = min(credit.remaining_amount, remaining_to_cover)
        if apply_amount <= 0:
            continue

        payment = Payment.objects.create(
            student=student,
            term=term,
            amount=apply_amount,
            payment_method=Payment.PaymentMethod.ADVANCE_CREDIT,
            paid_at=timezone.now(),
            payment_reference='',
            payment_notes=f'Applied from advance credit {credit.id}',
            recorded_by=recorded_by,
        )
        applied_payments.append(payment)

        credit.remaining_amount -= apply_amount
        if credit.remaining_amount == 0:
            credit.status = StudentFeeCredit.Status.APPLIED
        credit.save(update_fields=['remaining_amount', 'status', 'updated_at'])
        remaining_to_cover -= apply_amount

    return applied_payments


@transaction.atomic
def apply_available_credits_for_term(*, school, term, recorded_by):
    """
    Apply available advances to students enrolled in the term after fees are billed.
    Creates advance_credit payments and reduces credit remaining balances (FIFO).
    """
    from students.models import ClassEnrollment, Student

    student_ids = (
        ClassEnrollment.objects.filter(term=term, student__school=school)
        .values_list('student_id', flat=True)
        .distinct()
    )
    applied_payments = []
    for student_id in student_ids:
        student = Student.objects.get(pk=student_id)
        applied_payments.extend(
            apply_available_credits_for_student(
                student=student,
                term=term,
                recorded_by=recorded_by,
                school=school,
            ),
        )
    return applied_payments
