"""Term paid totals from payment allocations (waterfall-aware)."""

from decimal import Decimal

from django.db.models import DecimalField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce

from fees.models import PaymentAllocation


def sum_paid_toward_term(*, student, term) -> Decimal:
    total = (
        PaymentAllocation.objects.filter(payment__student=student, term=term)
        .aggregate(total=Sum('amount'))['total']
    )
    return total or Decimal('0.00')


def paid_toward_term_subquery(*, term, student_id_outerref='student_id'):
    """Subquery of allocated paid amount for an OuterRef student_id."""
    decimal_field = DecimalField(max_digits=12, decimal_places=2)
    return Coalesce(
        Subquery(
            PaymentAllocation.objects.filter(
                payment__student_id=OuterRef(student_id_outerref),
                term=term,
            )
            .values('payment__student_id')
            .annotate(total=Sum('amount'))
            .values('total')[:1],
            output_field=decimal_field,
        ),
        Value(Decimal('0.00')),
        output_field=decimal_field,
    )
