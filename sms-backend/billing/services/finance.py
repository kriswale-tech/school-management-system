"""School-facing SaaS finance totals for platform operators."""

from decimal import Decimal

from django.db.models import F, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from billing.models import Invoice, Payment, SchoolSubscription

_ZERO = Decimal('0.00')


def _money(value) -> str:
    amount = Decimal(value if value is not None else 0).quantize(Decimal('0.01'))
    return f'{amount:.2f}'


def school_is_overdue(school) -> bool:
    """Same rule as the school directory: past-due subscription or an open invoice past due."""
    subscription = SchoolSubscription.objects.filter(school=school, is_current=True).first()
    if subscription is not None and (
        subscription.status == SchoolSubscription.Status.PAST_DUE
        or subscription.billing_suspended_school
    ):
        return True
    return Invoice.objects.filter(
        school=school,
        status=Invoice.Status.OPEN,
        due_at__lt=timezone.now(),
        total_ghs__gt=F('amount_paid_ghs'),
    ).exists()


def school_finance_summary(school) -> dict:
    invoices = Invoice.objects.filter(school=school)
    # Void, draft, and uncollectible charges are not money the school still owes.
    counted = invoices.filter(status__in=(Invoice.Status.PAID, Invoice.Status.OPEN))
    billed = counted.aggregate(total=Sum('total_ghs'))['total']
    discount = counted.aggregate(total=Sum('discount_ghs'))['total']
    outstanding = invoices.filter(status=Invoice.Status.OPEN).aggregate(
        total=Coalesce(Sum(F('total_ghs') - F('amount_paid_ghs')), _ZERO),
    )['total']
    payments = Payment.objects.filter(school=school, status=Payment.Status.SUCCESS)
    total_paid = payments.aggregate(total=Sum('amount_ghs'))['total']
    by_purpose = {
        row['purpose']: _money(row['total'])
        for row in payments.values('purpose').annotate(total=Sum('amount_ghs'))
    }
    return {
        'total_paid_ghs': _money(total_paid),
        'outstanding_ghs': _money(outstanding),
        'billed_ghs': _money(billed),
        'discount_ghs': _money(discount),
        'successful_payments': payments.count(),
        'open_invoices': invoices.filter(status=Invoice.Status.OPEN).count(),
        'paid_invoices': invoices.filter(status=Invoice.Status.PAID).count(),
        'invoice_count': counted.count(),
        'payment_overdue': school_is_overdue(school),
        'by_purpose': by_purpose,
    }
