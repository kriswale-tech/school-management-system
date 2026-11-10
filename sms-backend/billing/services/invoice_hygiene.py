from __future__ import annotations

from django.db import transaction
from django.db.models import Count

from billing.models import Invoice, InvoiceLine


@transaction.atomic
def void_obsolete_interval_change_invoices(*, school=None) -> int:
    """Void open mid-period interval-change invoices (feature retired)."""
    qs = Invoice.objects.filter(
        status=Invoice.Status.OPEN,
        lines__kind=InvoiceLine.Kind.INTERVAL_CHANGE,
    )
    if school is not None:
        qs = qs.filter(school=school)
    ids = list(qs.values_list('pk', flat=True).distinct())
    if not ids:
        return 0
    return Invoice.objects.filter(pk__in=ids).update(status=Invoice.Status.VOID)


@transaction.atomic
def void_duplicate_open_invoices(*, school=None) -> int:
    """Keep the newest open invoice per school+notes fingerprint; void older clones.

    Targets accidental duplicate creates (same notes + total), not distinct charges.
    """
    base = Invoice.objects.filter(status=Invoice.Status.OPEN)
    if school is not None:
        base = base.filter(school=school)

    # Interval-change opens are handled separately.
    base = base.exclude(lines__kind=InvoiceLine.Kind.INTERVAL_CHANGE)

    groups = (
        base.values('school_id', 'notes', 'total_ghs')
        .annotate(c=Count('id'))
        .filter(c__gt=1)
    )
    voided = 0
    for group in groups:
        twins = list(
            Invoice.objects.filter(
                school_id=group['school_id'],
                notes=group['notes'],
                total_ghs=group['total_ghs'],
                status=Invoice.Status.OPEN,
            )
            .order_by('-created_at')
            .values_list('pk', flat=True)
        )
        if len(twins) < 2:
            continue
        obsolete = twins[1:]
        voided += Invoice.objects.filter(pk__in=obsolete).update(status=Invoice.Status.VOID)
    return voided


def sanitize_school_invoices(school) -> dict:
    interval_voided = void_obsolete_interval_change_invoices(school=school)
    duplicate_voided = void_duplicate_open_invoices(school=school)
    return {
        'interval_change_voided': interval_voided,
        'duplicate_open_voided': duplicate_voided,
    }
