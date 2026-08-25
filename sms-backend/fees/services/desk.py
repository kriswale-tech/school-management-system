from decimal import Decimal

from django.db.models import DecimalField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce

from fees.models import FeeStructure, Payment, StudentFeeCredit
from schools.models import AcademicYear, Term
from students.services import list_enrollments_for_term, resolve_term


def annotate_last_transaction(queryset, *, term):
    """Latest payment time for the term via subquery (no join inflation)."""
    paid_at_sq = (
        Payment.objects.filter(student_id=OuterRef('student_id'), term=term)
        .order_by('-paid_at')
        .values('paid_at')[:1]
    )
    return queryset.annotate(last_transaction_at=Subquery(paid_at_sq))


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


def list_fee_desk_rows(*, school, term):
    """Enrollments for a term with billed/paid totals, last payment, and advance."""
    queryset = list_enrollments_for_term(school=school, term=term)
    queryset = annotate_last_transaction(queryset, term=term)
    return annotate_advance_balance(queryset)


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
