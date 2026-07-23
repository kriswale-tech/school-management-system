from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import NotFound, ValidationError

from fees.models import FeeItem, FeeStructure
from fees.services.fees import get_or_create_fee_structure, validate_fee_structure_ready
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


def _resolve_applies_to_name(fee_item):
    from academics.models import ClassLevel, Level

    if fee_item.applies_to_type == FeeItem.AppliesToType.SCHOOL:
        return 'Entire School'
    if fee_item.applies_to_type == FeeItem.AppliesToType.LEVEL:
        level = Level.objects.filter(
            id=fee_item.applies_to_id,
            school=fee_item.fee_structure.school,
        ).first()
        return level.name if level else None
    if fee_item.applies_to_type == FeeItem.AppliesToType.CLASS:
        class_level = ClassLevel.objects.filter(
            id=fee_item.applies_to_id,
            school=fee_item.fee_structure.school,
        ).first()
        return class_level.name if class_level else None
    return None


def _serialize_fee_item(fee_item):
    return {
        'id': fee_item.id,
        'name': fee_item.name,
        'amount': fee_item.amount,
        'description': fee_item.description,
        'applies_to_type': fee_item.applies_to_type,
        'applies_to_type_display': fee_item.get_applies_to_type_display(),
        'applies_to_id': fee_item.applies_to_id,
        'applies_to_name': _resolve_applies_to_name(fee_item),
        'student_type': fee_item.student_type,
        'student_type_display': fee_item.get_student_type_display(),
    }


def _serialize_fee_structure(fee_structure):
    return {
        'id': fee_structure.id,
        'name': fee_structure.name,
        'status': fee_structure.status,
        'status_display': fee_structure.get_status_display(),
        'is_editable': fee_structure.is_editable,
        'is_locked': fee_structure.is_locked,
        'term_id': fee_structure.term_id,
        'term_name': fee_structure.term.get_term_display(),
        'academic_year': fee_structure.term.academic_year.academic_year,
    }


def get_fees_setup(school, *, created_by):
    term = _get_active_term(school)
    fee_structure = get_or_create_fee_structure(
        school=school,
        term=term,
        created_by=created_by,
    )
    fee_items = fee_structure.fee_items.order_by('name')

    return {
        'fee_structure': _serialize_fee_structure(fee_structure),
        'fee_items': [_serialize_fee_item(item) for item in fee_items],
    }


def _get_editable_fee_item(school, fee_item_id):
    try:
        fee_item = FeeItem.objects.select_related(
            'fee_structure',
            'fee_structure__term',
            'fee_structure__term__academic_year',
        ).get(
            id=fee_item_id,
            fee_structure__school=school,
        )
    except FeeItem.DoesNotExist as exc:
        raise NotFound('Fee item not found.') from exc

    if fee_item.fee_structure.is_locked:
        raise ValidationError('Fee items cannot be changed after the structure is applied.')
    return fee_item


def _get_editable_fee_structure(school, *, created_by):
    term = _get_active_term(school)
    fee_structure = get_or_create_fee_structure(
        school=school,
        term=term,
        created_by=created_by,
    )
    if fee_structure.is_locked:
        raise ValidationError('Fee items cannot be changed after the structure is applied.')
    return fee_structure


def create_fee_item(
    school,
    *,
    created_by,
    name,
    amount,
    applies_to_type,
    student_type=FeeItem.StudentType.ALL_STUDENTS,
    description='',
    applies_to_id=None,
):
    fee_structure = _get_editable_fee_structure(school, created_by=created_by)

    fee_item = FeeItem(
        fee_structure=fee_structure,
        name=name,
        amount=Decimal(amount),
        description=description,
        applies_to_type=applies_to_type,
        applies_to_id=applies_to_id,
        student_type=student_type,
    )
    try:
        fee_item.save()
    except DjangoValidationError as exc:
        _raise_drf(exc)

    return _serialize_fee_item(fee_item)


def update_fee_item(
    school,
    *,
    fee_item_id,
    name=None,
    amount=None,
    description=None,
    applies_to_type=None,
    applies_to_id=None,
    student_type=None,
):
    fee_item = _get_editable_fee_item(school, fee_item_id)

    if name is not None:
        fee_item.name = name
    if amount is not None:
        fee_item.amount = Decimal(amount)
    if description is not None:
        fee_item.description = description
    if applies_to_type is not None:
        fee_item.applies_to_type = applies_to_type
    if applies_to_id is not None or applies_to_type == FeeItem.AppliesToType.SCHOOL:
        if applies_to_type == FeeItem.AppliesToType.SCHOOL:
            fee_item.applies_to_id = None
        elif applies_to_id is not None:
            fee_item.applies_to_id = applies_to_id
    if student_type is not None:
        fee_item.student_type = student_type

    try:
        fee_item.save()
    except DjangoValidationError as exc:
        _raise_drf(exc)

    return _serialize_fee_item(fee_item)


def delete_fee_item(school, *, fee_item_id):
    fee_item = _get_editable_fee_item(school, fee_item_id)
    fee_item.delete()


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
