from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce

from fees.models import Payment, StudentFee, StudentFeeCredit
from fees.services.credits import create_credit_from_excess, get_student_advance_balance
from schools.models import School, Term
from students.models import Student


BACKFILL_NOTE_PREFIX = 'Backfilled from historical overpayment'


def _term_cash_totals(*, student, term):
    billed = (
        StudentFee.objects.filter(student=student, term=term).aggregate(
            total=Coalesce(Sum('amount'), Decimal('0.00')),
        )['total']
        or Decimal('0.00')
    )
    paid = (
        Payment.objects.filter(student=student, term=term)
        .exclude(payment_method=Payment.PaymentMethod.ADVANCE_CREDIT)
        .aggregate(
            total=Coalesce(Sum('amount'), Decimal('0.00')),
        )['total']
        or Decimal('0.00')
    )
    return billed, paid, paid - billed


def _credits_already_for_term(*, student, term):
    """Original credit amounts already tied to cash payments on this term."""
    return (
        StudentFeeCredit.objects.filter(
            student=student,
            source_payment__term=term,
        )
        .exclude(status=StudentFeeCredit.Status.REFUNDED)
        .aggregate(
            total=Coalesce(Sum('amount'), Decimal('0.00')),
        )['total']
        or Decimal('0.00')
    )


def reconcile_duplicate_backfill_credits_for_school(*, school, dry_run=False):
    """
    Remove backfill credits that double-count excess already covered by a
    live (non-backfill) advance on the same term.
    """
    removed = []
    students = Student.objects.filter(school=school).order_by('last_name', 'first_name')
    terms = (
        Term.objects.filter(school=school)
        .select_related('academic_year')
        .order_by('start_date')
    )

    for student in students:
        for term in terms:
            _, _, excess = _term_cash_totals(student=student, term=term)
            if excess <= 0:
                continue

            already = _credits_already_for_term(student=student, term=term)
            if already <= excess:
                continue

            over = already - excess
            backfill_credits = list(
                StudentFeeCredit.objects.filter(
                    student=student,
                    source_payment__term=term,
                    notes__startswith=BACKFILL_NOTE_PREFIX,
                )
                .exclude(status=StudentFeeCredit.Status.REFUNDED)
                .order_by('-created_at')
            )

            for credit in backfill_credits:
                if over <= 0:
                    break
                entry = {
                    'student_id': str(student.id),
                    'student': str(student),
                    'term': f'{term.academic_year.academic_year} · {term.get_term_display()}',
                    'credit_id': str(credit.id),
                    'amount': credit.amount,
                }
                if not dry_run:
                    credit.delete()
                removed.append(entry)
                over -= credit.amount

    return removed


def backfill_advances_for_school(*, school, dry_run=False):
    """
    For each student/term where cash payments exceed billed fees, create an
    available advance credit for the uncovered excess (skipping advance_credit
    payments).

    Idempotent: amounts already credited for that term (live payment advances
    or prior backfills) are subtracted from the excess before creating anything.
    """
    created = []
    skipped = []

    students = Student.objects.filter(school=school).order_by('last_name', 'first_name')
    terms = (
        Term.objects.filter(school=school)
        .select_related('academic_year')
        .order_by('start_date')
    )

    for student in students:
        for term in terms:
            billed, paid, excess = _term_cash_totals(student=student, term=term)
            if excess <= 0:
                continue

            already_credited = _credits_already_for_term(student=student, term=term)
            uncovered = excess - already_credited
            if uncovered <= 0:
                skipped.append({
                    'student_id': str(student.id),
                    'student': str(student),
                    'term': f'{term.academic_year.academic_year} · {term.get_term_display()}',
                    'excess': excess,
                    'already_credited': already_credited,
                    'reason': 'already_covered',
                })
                continue

            source_payment = (
                Payment.objects.filter(student=student, term=term)
                .exclude(payment_method=Payment.PaymentMethod.ADVANCE_CREDIT)
                .order_by('-paid_at')
                .first()
            )

            entry = {
                'student_id': str(student.id),
                'student': str(student),
                'term': f'{term.academic_year.academic_year} · {term.get_term_display()}',
                'billed': billed,
                'paid': paid,
                'excess': excess,
                'uncovered': uncovered,
            }

            if dry_run:
                created.append(entry)
                continue

            with transaction.atomic():
                credit = create_credit_from_excess(
                    school=school,
                    student=student,
                    amount=uncovered,
                    source_payment=source_payment,
                )
                if credit is not None:
                    credit.notes = (
                        f'{BACKFILL_NOTE_PREFIX} '
                        f'({paid} paid vs {billed} billed for term {term.id}).'
                    )
                    credit.save(update_fields=['notes', 'updated_at'])
                    entry['credit_id'] = str(credit.id)
                    entry['advance_balance'] = get_student_advance_balance(student=student)
                    created.append(entry)

    return {'created': created, 'skipped': skipped}


def backfill_advances(*, school_id=None, dry_run=False, reconcile=True):
    schools = School.objects.all().order_by('name')
    if school_id:
        schools = schools.filter(id=school_id)

    results = []
    for school in schools:
        removed = []
        if reconcile:
            removed = reconcile_duplicate_backfill_credits_for_school(
                school=school,
                dry_run=dry_run,
            )
        result = backfill_advances_for_school(school=school, dry_run=dry_run)
        results.append({
            'school_id': str(school.id),
            'school': school.name,
            'removed': removed,
            **result,
        })
    return results
