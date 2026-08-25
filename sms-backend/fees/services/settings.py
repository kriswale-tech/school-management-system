from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import NotFound, ValidationError

from fees.models import FeeItem, FeeStructure
from fees.services.fees import (
    apply_fee_structure,
    get_or_create_fee_structure,
    publish_fee_structure,
)
from students.services import resolve_term


def _raise_drf(exc: DjangoValidationError):
    if hasattr(exc, 'message_dict'):
        raise ValidationError(exc.message_dict) from exc
    if hasattr(exc, 'messages'):
        raise ValidationError(list(exc.messages)) from exc
    raise ValidationError(str(exc)) from exc


def is_term_ended(term, *, today=None) -> bool:
    today = today or date.today()
    return term.end_date < today


def _ensure_term_allows_mutations(term):
    if is_term_ended(term):
        raise ValidationError({
            'term': 'Past terms are read-only. Fee catalogs cannot be changed or applied.',
        })


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


def serialize_fee_item(fee_item):
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
        'term_id': fee_item.fee_structure.term_id,
        'term_name': fee_item.fee_structure.term.get_term_display(),
        'academic_year': fee_item.fee_structure.term.academic_year.academic_year,
    }


def serialize_fee_structure(fee_structure, *, fee_items=None):
    if fee_items is None:
        fee_items = list(fee_structure.fee_items.order_by('name'))
    item_count = len(fee_items)
    term_ended = is_term_ended(fee_structure.term)
    return {
        'id': fee_structure.id,
        'name': fee_structure.name,
        'status': fee_structure.status,
        'status_display': fee_structure.get_status_display(),
        'is_editable': fee_structure.is_editable and not term_ended,
        'is_locked': fee_structure.is_locked,
        'term_ended': term_ended,
        'can_apply': (
            not fee_structure.is_locked
            and item_count > 0
            and not term_ended
        ),
        'item_count': item_count,
        'term_id': fee_structure.term_id,
        'term_name': fee_structure.term.get_term_display(),
        'academic_year': fee_structure.term.academic_year.academic_year,
        'applied_at': fee_structure.applied_at,
    }


def serialize_structure_detail(fee_structure):
    fee_structure = FeeStructure.objects.select_related(
        'term',
        'term__academic_year',
    ).get(pk=fee_structure.pk)
    fee_items = list(
        FeeItem.objects.filter(fee_structure=fee_structure)
        .select_related('fee_structure__term', 'fee_structure__term__academic_year')
        .order_by('name')
    )
    return {
        'fee_structure': serialize_fee_structure(fee_structure, fee_items=fee_items),
        'fee_items': [serialize_fee_item(item) for item in fee_items],
    }


def get_fee_structure_detail(*, school, created_by, term_id=None):
    term = resolve_term(school, term_id)
    existing = FeeStructure.objects.filter(school=school, term=term).first()

    if is_term_ended(term):
        if existing is None:
            raise ValidationError({
                'term': 'Cannot create a fee catalog for a past term.',
            })
        return serialize_structure_detail(existing)

    fee_structure = get_or_create_fee_structure(
        school=school,
        term=term,
        created_by=created_by,
    )
    return serialize_structure_detail(fee_structure)


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
    _ensure_term_allows_mutations(fee_item.fee_structure.term)
    return fee_item


def _get_editable_structure_for_term(*, school, term, created_by):
    _ensure_term_allows_mutations(term)
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
    term_id=None,
):
    term = resolve_term(school, term_id)
    fee_structure = _get_editable_structure_for_term(
        school=school,
        term=term,
        created_by=created_by,
    )

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

    fee_item = FeeItem.objects.select_related(
        'fee_structure',
        'fee_structure__term',
        'fee_structure__term__academic_year',
    ).get(pk=fee_item.pk)
    return serialize_fee_item(fee_item)


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

    return serialize_fee_item(fee_item)


def delete_fee_item(school, *, fee_item_id):
    fee_item = _get_editable_fee_item(school, fee_item_id)
    fee_item.delete()


def apply_structure(*, school, structure_id):
    try:
        fee_structure = FeeStructure.objects.select_related(
            'term',
            'term__academic_year',
        ).get(id=structure_id, school=school)
    except FeeStructure.DoesNotExist as exc:
        raise NotFound('Fee structure not found.') from exc

    if fee_structure.is_locked:
        raise ValidationError('This fee structure has already been applied.')
    _ensure_term_allows_mutations(fee_structure.term)

    try:
        if fee_structure.status == FeeStructure.Status.DRAFT:
            publish_fee_structure(fee_structure)
        apply_fee_structure(fee_structure)
    except DjangoValidationError as exc:
        _raise_drf(exc)

    return serialize_structure_detail(fee_structure)
