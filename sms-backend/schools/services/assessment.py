from copy import deepcopy
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

from academics.models import Level
from assessments.constants.grade_templates import (
    BECE_STANDARD_NUMERICAL_GRADES,
    GES_INTERNAL_LETTER_GRADES,
)
from assessments.models import AssessmentConfig
from assessments.services.assessment_config import (
    replace_grade_bands,
    validate_assessment_config_ready,
)
from schools.models import SchoolSetup
from schools.services.setup import advance_setup_if_needed, require_prior_setup_steps


def _raise_drf(exc: DjangoValidationError):
    if hasattr(exc, 'message_dict'):
        raise ValidationError(exc.message_dict) from exc
    if hasattr(exc, 'messages'):
        raise ValidationError(list(exc.messages)) from exc
    raise ValidationError(str(exc)) from exc


def _serialize_grade_band(band):
    return {
        'id': band.id,
        'grade': band.grade,
        'min_score': band.min_score,
        'max_score': band.max_score,
        'remark': band.remark,
    }


def _serialize_config(config):
    return {
        'id': config.id,
        'continuous_assessment_weight': config.continuous_assessment_weight,
        'exam_weight': config.exam_weight,
        'result_type': config.result_type,
        'grade_type': config.grade_type,
        'grade_bands': [
            _serialize_grade_band(band)
            for band in config.grade_bands.all()
        ],
    }


def _serialize_level_assessment(level, config=None):
    return {
        'level_id': level.id,
        'level_name': level.name,
        'level_order': level.order,
        'config': _serialize_config(config) if config is not None else None,
    }


def get_assessment_setup(school):
    levels = list(
        Level.objects.filter(school=school, is_active=True)
        .order_by('order', 'name')
    )
    configs_by_level_id = {
        config.level_id: config
        for config in AssessmentConfig.objects.filter(
            level__school=school,
            level__is_active=True,
        ).prefetch_related('grade_bands')
    }

    return {
        'grade_templates': {
            'letter': deepcopy(GES_INTERNAL_LETTER_GRADES),
            'numerical': deepcopy(BECE_STANDARD_NUMERICAL_GRADES),
        },
        'levels': [
            _serialize_level_assessment(
                level,
                configs_by_level_id.get(level.id),
            )
            for level in levels
        ],
    }


def _get_active_level(school, level_id):
    try:
        return Level.objects.get(id=level_id, school=school, is_active=True)
    except Level.DoesNotExist as exc:
        raise NotFound('Level not found.') from exc


@transaction.atomic
def save_level_assessment_config(
    school,
    *,
    level_id,
    continuous_assessment_weight,
    exam_weight,
    result_type,
    grade_type=None,
    grade_bands=None,
):
    school_setup, _ = SchoolSetup.objects.get_or_create(school=school)
    require_prior_setup_steps(
        school_setup,
        SchoolSetup.SetupStep.ASSESSMENT,
    )

    level = _get_active_level(school, level_id)
    grade_bands = grade_bands or []
    uses_grades = result_type in AssessmentConfig.GRADE_RESULT_TYPES

    try:
        config = AssessmentConfig.objects.select_for_update().get(level=level)
    except AssessmentConfig.DoesNotExist:
        config = AssessmentConfig(level=level)

    config.continuous_assessment_weight = Decimal(continuous_assessment_weight)
    config.exam_weight = Decimal(exam_weight)
    config.result_type = result_type

    try:
        if uses_grades:
            config.grade_type = grade_type
            config.save()
            replace_grade_bands(config, grade_bands)
        else:
            config.grade_type = None
            if config.pk:
                config.grade_bands.all().delete()
            config.save()
    except DjangoValidationError as exc:
        _raise_drf(exc)

    config.refresh_from_db()
    return _serialize_level_assessment(level, config)


def validate_assessment_setup_ready(school):
    levels = list(
        Level.objects.filter(school=school, is_active=True)
        .order_by('order', 'name')
    )
    configs_by_level_id = {
        config.level_id: config
        for config in AssessmentConfig.objects.filter(
            level__school=school,
            level__is_active=True,
        ).prefetch_related('grade_bands')
    }

    errors = []
    for level in levels:
        config = configs_by_level_id.get(level.id)
        if config is None:
            errors.append(
                f"Level '{level.name}' has no assessment configuration.",
            )
            continue
        try:
            validate_assessment_config_ready(config)
        except DjangoValidationError as exc:
            if hasattr(exc, 'messages'):
                detail = '; '.join(str(message) for message in exc.messages)
            else:
                detail = str(exc)
            errors.append(f"Level '{level.name}': {detail}")

    if errors:
        raise ValidationError({'detail': errors})


def complete_assessment_setup(school):
    school_setup, _ = SchoolSetup.objects.get_or_create(school=school)
    require_prior_setup_steps(
        school_setup,
        SchoolSetup.SetupStep.ASSESSMENT,
    )
    validate_assessment_setup_ready(school)
    return advance_setup_if_needed(
        school_setup,
        SchoolSetup.SetupStep.ASSESSMENT,
    )
