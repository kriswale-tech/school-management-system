from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError

from fees.models import FeeStructure
from fees.services.fees import validate_fee_structure_ready
from fees.services.settings import (
    create_fee_item as create_structure_fee_item,
    delete_fee_item as delete_structure_fee_item,
    get_fee_structure_detail,
    update_fee_item as update_structure_fee_item,
)
from schools.models import SchoolSetup, Term
from schools.services.setup import advance_setup_if_needed, require_prior_setup_steps


def _raise_drf(exc: DjangoValidationError):
    if hasattr(exc, 'message_dict'):
        raise ValidationError(exc.message_dict) from exc
    if hasattr(exc, 'messages'):
        raise ValidationError(list(exc.messages)) from exc
    raise ValidationError(str(exc)) from exc


def _get_active_term(school):
    term = Term.objects.filter(school=school, is_active=True).select_related(
        'academic_year',
    ).first()
    if term is None:
        raise ValidationError({
            'detail': 'Set an active term before configuring fees.',
        })
    return term


def get_fees_setup(school, *, created_by):
    return get_fee_structure_detail(school=school, created_by=created_by)


def create_fee_item(school, *, created_by, **kwargs):
    return create_structure_fee_item(school, created_by=created_by, **kwargs)


def update_fee_item(school, **kwargs):
    return update_structure_fee_item(school, **kwargs)


def delete_fee_item(school, *, fee_item_id):
    delete_structure_fee_item(school, fee_item_id=fee_item_id)


def validate_fees_setup_ready(school):
    term = _get_active_term(school)
    fee_structure = FeeStructure.objects.filter(school=school, term=term).first()
    if fee_structure is None:
        raise ValidationError({
            'detail': 'Add at least one fee item before completing fees setup.',
        })

    try:
        validate_fee_structure_ready(fee_structure)
    except DjangoValidationError as exc:
        _raise_drf(exc)


def complete_fees_setup(school):
    school_setup, _ = SchoolSetup.objects.get_or_create(school=school)
    require_prior_setup_steps(
        school_setup,
        SchoolSetup.SetupStep.FEES,
    )
    validate_fees_setup_ready(school)

    return advance_setup_if_needed(
        school_setup,
        SchoolSetup.SetupStep.FEES,
    )


def apply_active_term_fees(school):
    """
    Publish (if needed) and apply the active-term fee structure so enrolled
    students receive StudentFee rows. No-op if already applied.
    """
    from fees.services import apply_fee_structure, publish_fee_structure

    term = _get_active_term(school)
    fee_structure = (
        FeeStructure.objects.filter(school=school, term=term)
        .prefetch_related('fee_items')
        .first()
    )
    if fee_structure is None:
        raise ValidationError({
            'detail': 'Add at least one fee item before finishing setup.',
        })

    if fee_structure.is_locked:
        return fee_structure

    try:
        if fee_structure.status == FeeStructure.Status.DRAFT:
            publish_fee_structure(fee_structure)
        apply_fee_structure(fee_structure)
    except DjangoValidationError as exc:
        _raise_drf(exc)

    return fee_structure
