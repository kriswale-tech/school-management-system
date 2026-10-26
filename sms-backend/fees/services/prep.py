"""Accountant next-term fee preparation status (lead window before term end)."""

from datetime import date

from fees.models import FeeStructure
from schools.models import Term
from schools.services.academic_calendar import expected_next_term
from schools.services.term_transition import TRANSITION_LEAD_DAYS


def next_term_fee_prep_status(school, *, today=None):
    """Status for the accountant fee-prep banner.

    Accountant is done once the next catalog is published (or already applied).
    Apply/lock still happens when admin opens the next term.
    """
    today = today or date.today()
    active = Term.objects.filter(school=school, is_active=True).select_related(
        'academic_year',
    ).first()
    empty = {
        'visible': False,
        'done': True,
        'urgency': None,
        'days_remaining': None,
        'term_ends_on': None,
        'current_term_label': None,
        'next_term_id': None,
        'next_term_label': None,
        'fee_status': None,
        'item_count': 0,
        'summary': '',
        'href': '/fees/settings',
    }
    if active is None:
        return empty

    days_remaining = (active.end_date - today).days
    if days_remaining > TRANSITION_LEAD_DAYS:
        return empty

    target = expected_next_term(active)
    current_label = f'{active.get_term_display()} {active.academic_year.academic_year}'

    if target is None:
        return {
            **empty,
            'visible': True,
            'done': False,
            'urgency': 'red' if days_remaining <= 0 else 'amber',
            'days_remaining': days_remaining,
            'term_ends_on': active.end_date.isoformat(),
            'current_term_label': current_label,
            'fee_status': 'no_next_term',
            'summary': (
                'The next term is not on the calendar yet. Ask an admin to add it '
                'before fee items can be set up.'
            ),
            'href': '/fees/settings',
        }

    next_label = f'{target.get_term_display()} {target.academic_year.academic_year}'
    href = f'/fees/settings?term={target.id}'
    structure = FeeStructure.objects.filter(school=school, term=target).first()
    item_count = structure.fee_items.count() if structure else 0

    if structure is None or item_count == 0:
        fee_status = 'missing' if structure is None else 'empty'
        summary = (
            f'{next_label} has no fee items yet. Copy from the current term or add items, '
            'then publish.'
        )
        done = False
    elif structure.status == FeeStructure.Status.APPLIED:
        fee_status = 'applied'
        summary = f'Fees for {next_label} are applied and locked.'
        done = True
    elif structure.status == FeeStructure.Status.PUBLISHED:
        fee_status = 'published'
        summary = (
            f'Fees for {next_label} are published and ready. An admin will apply them '
            'when opening the next term.'
        )
        done = True
    else:
        # draft or carried_forward with items
        fee_status = structure.status
        summary = (
            f'{next_label} has {item_count} fee item'
            f'{"s" if item_count != 1 else ""}. Review amounts and publish when ready.'
        )
        done = False

    return {
        'visible': True,
        'done': done,
        'urgency': 'red' if days_remaining <= 0 else 'amber',
        'days_remaining': days_remaining,
        'term_ends_on': active.end_date.isoformat(),
        'current_term_label': current_label,
        'next_term_id': str(target.id),
        'next_term_label': next_label,
        'fee_status': fee_status,
        'item_count': item_count,
        'summary': summary,
        'href': href,
    }
