from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from django.db.models import Sum

from fees.models import Payment, PaymentAllocation, Receipt, StudentFee
from fees.services.credits import create_credit_from_excess, get_student_advance_balance
from fees.services.fees import get_student_term_balance
from schools.models import Term
from students.services import school_initials


def _term_label(term):
    return f'{term.academic_year.academic_year} · {term.get_term_display()}'


def get_student_all_time_balance(*, student) -> dict:
    """Lifetime billed/paid and remaining balance for a student."""
    billed = (
        StudentFee.objects.filter(student=student).aggregate(total=Sum('amount'))['total']
        or Decimal('0.00')
    )
    paid = (
        Payment.objects.filter(student=student).aggregate(total=Sum('amount'))['total']
        or Decimal('0.00')
    )
    return {
        'total_billed': billed,
        'total_paid': paid,
        'balance': max(billed - paid, Decimal('0.00')),
    }


def list_student_outstanding_term_balances(*, school, student) -> list[dict]:
    """Terms (earliest first) where the student still has a positive balance."""
    terms = (
        Term.objects.filter(school=school)
        .select_related('academic_year')
        .order_by('start_date')
    )
    rows = []
    for term in terms:
        balance = get_student_term_balance(student=student, term=term)['balance']
        if balance > 0:
            rows.append({
                'term': term,
                'term_label': _term_label(term),
                'balance': balance,
            })
    return rows


def format_outstanding_terms_summary(rows: list[dict], *, max_terms: int = 4) -> str:
    """Compact "Term: GHS x; …" string for SMS / preview."""
    if not rows:
        return ''
    parts = [
        f"{row['term_label']}: GHS {row['balance']:.2f}"
        for row in rows[:max_terms]
    ]
    leftover = len(rows) - max_terms
    if leftover > 0:
        parts.append(f'+{leftover} more')
    return '; '.join(parts)


def get_earliest_outstanding_term(*, school, student):
    """Return the earliest term (by start_date) where the student still owes fees."""
    rows = list_student_outstanding_term_balances(school=school, student=student)
    if not rows:
        return None, None
    first = rows[0]
    return first['term'], get_student_term_balance(student=student, term=first['term'])


def build_student_payment_target(*, school, student):
    """Payment target context for the record-payment form."""
    from students.services import get_enrollment_for_student, get_active_term

    outstanding_rows = list_student_outstanding_term_balances(school=school, student=student)
    all_time = get_student_all_time_balance(student=student)
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
    outstanding_terms = [
        {
            'term_id': row['term'].id,
            'term_label': row['term_label'],
            'balance': row['balance'],
        }
        for row in outstanding_rows
    ]

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
        'all_time_outstanding': all_time['balance'],
        'has_all_time_outstanding': all_time['balance'] > 0,
        'outstanding_terms': outstanding_terms,
        'advance_balance': advance_balance,
        'has_advance': advance_balance > 0,
    }

    if not outstanding_rows:
        return payload

    term = outstanding_rows[0]['term']
    payload['has_outstanding'] = True
    payload['outstanding_balance'] = outstanding_rows[0]['balance']
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
    Apply a payment oldest-owing-term first (waterfall).

    Only leftover after every owing term is cleared becomes advance credit.
    """
    if amount is None or amount <= 0:
        raise ValidationError({'amount': 'Payment amount must be greater than zero.'})

    if payment_method == Payment.PaymentMethod.ADVANCE_CREDIT:
        raise ValidationError({
            'payment_method': 'Advance credit applications are system-generated only.',
        })

    owing_rows = list_student_outstanding_term_balances(school=school, student=student)
    if not owing_rows:
        raise ValidationError({
            'student': 'This student has no outstanding fees to pay.',
        })

    remaining = amount
    planned_allocations = []
    for row in owing_rows:
        if remaining <= 0:
            break
        apply_amount = min(remaining, row['balance'])
        if apply_amount <= 0:
            continue
        planned_allocations.append({
            'term': row['term'],
            'term_label': row['term_label'],
            'amount': apply_amount,
        })
        remaining -= apply_amount

    if not planned_allocations:
        raise ValidationError({
            'student': 'This student has no outstanding fees to pay.',
        })

    primary_term = planned_allocations[0]['term']
    payment = Payment(
        student=student,
        term=primary_term,
        amount=amount,
        payment_method=payment_method,
        paid_at=paid_at,
        payment_reference=payment_reference or '',
        payment_notes=payment_notes or '',
        recorded_by=recorded_by,
    )
    payment.save(skip_default_allocation=True)
    allocation_payload = []
    for plan in planned_allocations:
        PaymentAllocation.objects.create(
            payment=payment,
            term=plan['term'],
            amount=plan['amount'],
        )
        allocation_payload.append({
            'term_id': plan['term'].id,
            'term_label': plan['term_label'],
            'amount': plan['amount'],
        })

    receipt = Receipt.objects.create(
        payment=payment,
        receipt_number=_generate_receipt_number(school=school),
        issued_by=recorded_by,
    )

    excess_amount = remaining
    credit = None
    if excess_amount > 0:
        credit = create_credit_from_excess(
            school=school,
            student=student,
            amount=excess_amount,
            source_payment=payment,
        )

    amount_applied = amount - excess_amount
    _record_payment_activity(
        school=school,
        student=student,
        amount=amount,
        term=payment.term,
        recorded_by=recorded_by,
        payment=payment,
    )

    from notifications.services.guardians import schedule_payment_receipt_notice

    schedule_payment_receipt_notice(
        student_id=student.id,
        payment_id=payment.id,
        receipt_id=receipt.id,
        receipt_number=receipt.receipt_number,
        amount=amount,
    )

    return {
        'payment_id': payment.id,
        'receipt_id': receipt.id,
        'receipt_number': receipt.receipt_number,
        'term_id': payment.term_id,
        'term_label': _term_label(payment.term),
        'amount': amount,
        'amount_applied': amount_applied,
        'advance_created': excess_amount,
        'outstanding_after': get_student_all_time_balance(student=student)['balance'],
        'advance_balance': get_student_advance_balance(student=student),
        'credit_id': credit.id if credit else None,
        'paid_at': payment.paid_at,
        'allocations': allocation_payload,
    }


def _record_payment_activity(*, school, student, amount, term, recorded_by, payment):
    from activities.models import Activity
    from activities.services import record_activity

    from students.models import ClassEnrollment

    name = ' '.join(
        part for part in (student.first_name, student.other_names, student.last_name) if part
    ).strip()
    enrollment = (
        ClassEnrollment.objects.filter(student=student, term=term)
        .select_related('stream')
        .first()
        if term is not None
        else None
    )
    record_activity(
        school=school,
        actor=recorded_by,
        verb=Activity.Verb.PAYMENT_RECORDED,
        summary=f'Payment of GHS {amount} recorded for {name}.',
        href=f'/fees/{student.id}',
        term=term,
        stream=enrollment.stream if enrollment is not None else None,
        target_kind='payment',
        target_id=payment.id,
    )
