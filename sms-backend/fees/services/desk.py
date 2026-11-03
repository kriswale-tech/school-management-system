from decimal import Decimal

from django.db.models import (
    Case,
    CharField,
    DecimalField,
    F,
    OuterRef,
    Prefetch,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce

from fees.models import FeeStructure, Payment, StudentFee, StudentFeeCredit
from fees.services.ledger import paid_toward_term_subquery
from schools.models import AcademicYear, Term
from students.models import ClassEnrollment, StudentParent
from students.services import get_active_term, list_enrollments_for_term, resolve_term

FEE_DESK_ALL_TIME = 'all'


def annotate_last_transaction(queryset, *, term):
    """Latest payment time for the term via allocation subquery."""
    from fees.models import PaymentAllocation

    paid_at_sq = (
        PaymentAllocation.objects.filter(
            payment__student_id=OuterRef('student_id'),
            term=term,
        )
        .order_by('-payment__paid_at')
        .values('payment__paid_at')[:1]
    )
    return queryset.annotate(last_transaction_at=Subquery(paid_at_sq))


def annotate_last_transaction_all_time(queryset):
    """Latest payment time across all terms via subquery."""
    paid_at_sq = (
        Payment.objects.filter(student_id=OuterRef('student_id'))
        .order_by('-paid_at')
        .values('paid_at')[:1]
    )
    return queryset.annotate(last_transaction_at=Subquery(paid_at_sq))


def annotate_payment_totals_all_time(queryset):
    """Annotate lifetime billed/paid for each enrollment's student."""
    decimal_field = DecimalField(max_digits=12, decimal_places=2)
    billed_sq = (
        StudentFee.objects.filter(student_id=OuterRef('student_id'))
        .values('student_id')
        .annotate(total=Sum('amount'))
        .values('total')[:1]
    )
    paid_sq = (
        Payment.objects.filter(student_id=OuterRef('student_id'))
        .values('student_id')
        .annotate(total=Sum('amount'))
        .values('total')[:1]
    )
    return queryset.annotate(
        total_billed=Coalesce(
            Subquery(billed_sq, output_field=decimal_field),
            Value(Decimal('0.00')),
            output_field=decimal_field,
        ),
        total_paid=Coalesce(
            Subquery(paid_sq, output_field=decimal_field),
            Value(Decimal('0.00')),
            output_field=decimal_field,
        ),
    )


def annotate_payment_status(queryset):
    return queryset.annotate(
        payment_status=Case(
            When(
                total_billed__gt=0,
                total_paid__gte=F('total_billed'),
                then=Value('fully_paid'),
            ),
            When(total_paid__gt=0, then=Value('partially_paid')),
            When(total_billed__gt=0, then=Value('owing')),
            default=Value('no_fees'),
            output_field=CharField(),
        ),
    )


def annotate_advance_balance(queryset):
    """Available advance credit via subquery (no join inflation)."""
    decimal_field = DecimalField(max_digits=12, decimal_places=2)
    advance_sq = (
        StudentFeeCredit.objects.filter(
            student_id=OuterRef('student_id'),
            status=StudentFeeCredit.Status.AVAILABLE,
        )
        .values('student_id')
        .annotate(total=Sum('remaining_amount'))
        .values('total')[:1]
    )
    return queryset.annotate(
        advance_balance=Coalesce(
            Subquery(advance_sq, output_field=decimal_field),
            Value(Decimal('0.00')),
            output_field=decimal_field,
        ),
    )


def list_fee_desk_rows(*, school, term, all_time: bool = False):
    """Enrollments for a term with billed/paid totals, last payment, and advance.

    When ``all_time`` is true, money columns sum across every term for each
    student while the row set remains enrollments for ``term`` (usually active).
    """
    if all_time:
        queryset = (
            ClassEnrollment.objects.filter(
                student__school=school,
                term=term,
            )
            .select_related(
                'student',
                'class_level',
                'class_level__level',
                'stream',
            )
            .prefetch_related(
                Prefetch(
                    'student__parent_links',
                    queryset=StudentParent.objects.filter(
                        is_primary=True,
                    ).select_related('parent'),
                    to_attr='primary_parent_links',
                ),
            )
            .order_by('student__last_name', 'student__first_name')
        )
        queryset = annotate_payment_totals_all_time(queryset)
        queryset = annotate_payment_status(queryset)
        queryset = annotate_last_transaction_all_time(queryset)
        return annotate_advance_balance(queryset)

    queryset = list_enrollments_for_term(school=school, term=term)
    queryset = annotate_last_transaction(queryset, term=term)
    return annotate_advance_balance(queryset)


def list_fee_desk_debtor_ids(*, queryset) -> list:
    """Student UUIDs with outstanding balance in a (filtered) fee desk queryset."""
    from django.db.models import F

    return list(
        queryset.filter(total_billed__gt=F('total_paid'))
        .order_by('student__last_name', 'student__first_name', 'student_id')
        .values_list('student_id', flat=True),
    )


def get_fee_desk_stats(*, queryset):
    """Aggregate fees stats for a (possibly filtered) enrollment queryset."""
    from django.db.models import Count, F, Q

    aggregates = queryset.aggregate(
        total_students=Count('id'),
        total_expected=Coalesce(
            Sum('total_billed'),
            Value(Decimal('0.00')),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        total_collected=Coalesce(
            Sum('total_paid'),
            Value(Decimal('0.00')),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        debtors_count=Count(
            'id',
            filter=Q(total_billed__gt=F('total_paid')),
        ),
        students_in_credit=Count(
            'id',
            filter=Q(advance_balance__gt=0),
        ),
        total_advances=Coalesce(
            Sum('advance_balance'),
            Value(Decimal('0.00')),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
    )

    total_expected = aggregates['total_expected'] or Decimal('0.00')
    total_collected = aggregates['total_collected'] or Decimal('0.00')
    outstanding = max(total_expected - total_collected, Decimal('0.00'))

    return {
        'total_expected': total_expected,
        'total_collected': total_collected,
        'outstanding': outstanding,
        'debtors_count': aggregates['debtors_count'] or 0,
        'total_students': aggregates['total_students'] or 0,
        'students_in_credit': aggregates['students_in_credit'] or 0,
        'total_advances': aggregates['total_advances'] or Decimal('0.00'),
    }


def get_fee_filter_options(*, school):
    """Academic years and terms for fees desk/settings filters (active term flagged)."""
    from datetime import date

    today = date.today()
    years = (
        AcademicYear.objects.filter(school=school)
        .prefetch_related('terms', 'terms__fee_structures')
        .order_by('-start_date')
    )
    active_term = (
        Term.objects.filter(school=school, is_active=True)
        .select_related('academic_year')
        .first()
    )
    structure_term_ids = set(
        FeeStructure.objects.filter(school=school).values_list('term_id', flat=True),
    )

    year_payload = []
    term_options = []
    for year in years:
        terms = sorted(year.terms.all(), key=lambda item: item.start_date)
        term_rows = []
        for term in terms:
            label = f'{year.academic_year} · {term.get_term_display()}'
            is_ended = term.end_date < today
            has_fee_structure = term.id in structure_term_ids
            row = {
                'id': term.id,
                'term': term.term,
                'term_name': term.get_term_display(),
                'label': label,
                'is_active': bool(active_term and term.id == active_term.id),
                'is_ended': is_ended,
                'has_fee_structure': has_fee_structure,
                'academic_year_id': year.id,
                'academic_year': year.academic_year,
            }
            term_rows.append(row)
            term_options.append(row)
        year_payload.append({
            'id': year.id,
            'academic_year': year.academic_year,
            'is_active': year.is_active,
            'terms': term_rows,
        })

    return {
        'academic_years': year_payload,
        'terms': term_options,
        'active_term_id': active_term.id if active_term else None,
    }


def resolve_fee_desk_term(school, term_id=None):
    return resolve_term(school, term_id)


def resolve_fee_desk_scope(school, term_id=None):
    """Resolve desk term filter.

    Returns ``(term, all_time)``. ``term_id='all'`` uses the active-term
    enrollment roster with lifetime billed/paid totals.
    """
    raw = str(term_id).strip().lower() if term_id not in (None, '') else ''
    if raw == FEE_DESK_ALL_TIME:
        return get_active_term(school), True
    return resolve_term(school, term_id or None), False
