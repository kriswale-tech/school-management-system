from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from fees.models import Payment, Receipt
from fees.services.credits import create_credit_from_excess, get_student_advance_balance
from fees.services.fees import get_student_term_balance
from schools.models import Term
from students.services import school_initials


def _term_label(term):
    return f'{term.academic_year.academic_year} · {term.get_term_display()}'


def get_earliest_outstanding_term(*, school, student):
    """Return the earliest term (by start_date) where the student still owes fees."""
    terms = (
        Term.objects.filter(school=school)
        .select_related('academic_year')
        .order_by('start_date')
    )
    for term in terms:
        balance = get_student_term_balance(student=student, term=term)
        if balance['balance'] > 0:
            return term, balance
    return None, None


def build_student_payment_target(*, school, student):
    """Payment target context for the record-payment form."""
    from students.services import get_enrollment_for_student, get_active_term

    term, balance = get_earliest_outstanding_term(school=school, student=student)
    active_term = get_active_term(
        school,
        detail='Set an active term before recording payments.',
    )
    enrollment = get_enrollment_for_student(
        school=school,
        term=active_term,
        student=student,
    )
    class_display = None
    if enrollment:
        class_display = (
            enrollment.stream.full_name
            if enrollment.stream_id
            else enrollment.class_level.name
        )

    full_name = ' '.join(
        part for part in [student.first_name, student.other_names, student.last_name] if part
    ).strip()

    advance_balance = get_student_advance_balance(student=student)

    payload = {
        'student_id': student.id,
        'student': {
            'id': student.id,
            'student_id': student.student_id,
            'full_name': full_name,
            'class_display': class_display,
        },
        'target_term': None,
        'outstanding_balance': Decimal('0.00'),
        'has_outstanding': False,
        'advance_balance': advance_balance,
        'has_advance': advance_balance > 0,
    }

    if term is None:
        return payload

    payload['has_outstanding'] = True
    payload['outstanding_balance'] = balance['balance']
    payload['target_term'] = {
        'id': term.id,
        'term': term.term,
        'term_name': term.get_term_display(),
        'academic_year_id': term.academic_year_id,
        'academic_year': term.academic_year.academic_year,
        'label': _term_label(term),
    }
    return payload


def _generate_receipt_number(*, school):
    year = timezone.now().strftime('%Y')
    prefix = f'RCPT-{school_initials(school.name)}-{year}-'
    count = Receipt.objects.filter(
        payment__student__school=school,
        receipt_number__startswith=prefix,
    ).count()
    return f'{prefix}{count + 1:04d}'


@transaction.atomic
def record_student_payment(
    *,
    school,
    student,
    amount,
    payment_method,
    paid_at,
    recorded_by,
    payment_reference='',
    payment_notes='',
):
    """
    Record a payment against the earliest term with an outstanding balance.
    Any excess becomes available advance credit for later terms.
    """
    if amount is None or amount <= 0:
        raise ValidationError({'amount': 'Payment amount must be greater than zero.'})

    if payment_method == Payment.PaymentMethod.ADVANCE_CREDIT:
        raise ValidationError({
            'payment_method': 'Advance credit applications are system-generated only.',
        })

    term, balance = get_earliest_outstanding_term(school=school, student=student)
    if term is None:
        raise ValidationError({
            'student': 'This student has no outstanding fees to pay.',
        })

    owing = balance['balance']
    applied_amount = min(amount, owing)
    excess_amount = amount - applied_amount

    payment = Payment.objects.create(
        student=student,
        term=term,
        amount=amount,
        payment_method=payment_method,
        paid_at=paid_at,
        payment_reference=payment_reference or '',
        payment_notes=payment_notes or '',
        recorded_by=recorded_by,
    )

    receipt = Receipt.objects.create(
        payment=payment,
        receipt_number=_generate_receipt_number(school=school),
        issued_by=recorded_by,
    )

    credit = None
    if excess_amount > 0:
        credit = create_credit_from_excess(
            school=school,
            student=student,
            amount=excess_amount,
            source_payment=payment,
        )

    return {
        'payment_id': payment.id,
        'receipt_id': receipt.id,
        'receipt_number': receipt.receipt_number,
        'term_id': term.id,
        'term_label': _term_label(term),
        'amount': payment.amount,
        'amount_applied': applied_amount,
        'advance_created': excess_amount,
        'outstanding_after': max(owing - applied_amount, Decimal('0.00')),
        'advance_balance': get_student_advance_balance(student=student),
        'credit_id': credit.id if credit else None,
        'paid_at': payment.paid_at,
    }
