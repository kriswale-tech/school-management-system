from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from billing.models import Invoice, InvoiceLine, SchoolSubscription


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.01'))


@transaction.atomic
def create_invoice_with_lines(
    *,
    school,
    subscription: SchoolSubscription,
    period_start,
    period_end,
    lines: list[dict],
    status: str = Invoice.Status.OPEN,
    notes: str = '',
    mark_paid_if_zero: bool = True,
) -> Invoice:
    subtotal = Decimal('0.00')
    discount = Decimal('0.00')
    for line in lines:
        amount = _quantize(Decimal(str(line['amount_ghs'])))
        if line['kind'] == InvoiceLine.Kind.DISCOUNT:
            discount += abs(amount)
        else:
            subtotal += amount

    total = _quantize(max(Decimal('0.00'), subtotal - discount))
    now = timezone.now()
    invoice = Invoice.objects.create(
        school=school,
        subscription=subscription,
        currency='GHS',
        status=status,
        period_start=period_start,
        period_end=period_end,
        subtotal_ghs=subtotal,
        discount_ghs=discount,
        total_ghs=total,
        amount_paid_ghs=Decimal('0.00'),
        due_at=period_start,
        notes=notes,
    )
    for line in lines:
        InvoiceLine.objects.create(
            invoice=invoice,
            kind=line['kind'],
            description=line['description'],
            quantity=_quantize(Decimal(str(line.get('quantity', '1')))),
            unit_price_ghs=_quantize(Decimal(str(line.get('unit_price_ghs', line['amount_ghs'])))),
            amount_ghs=_quantize(Decimal(str(line['amount_ghs']))),
            metadata=line.get('metadata') or {},
        )

    if mark_paid_if_zero and total == 0:
        invoice.status = Invoice.Status.PAID
        invoice.amount_paid_ghs = Decimal('0.00')
        invoice.paid_at = now
        invoice.save(update_fields=['status', 'amount_paid_ghs', 'paid_at', 'updated_at'])

    return invoice


def mark_invoice_paid(invoice: Invoice, *, amount: Decimal | None = None) -> Invoice:
    amount = _quantize(amount if amount is not None else invoice.total_ghs)
    invoice.status = Invoice.Status.PAID
    invoice.amount_paid_ghs = amount
    invoice.paid_at = timezone.now()
    invoice.save(update_fields=['status', 'amount_paid_ghs', 'paid_at', 'updated_at'])
    return invoice
