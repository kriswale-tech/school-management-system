"""Term-scoped assessment structure (weights, result format, grade bands)."""

from __future__ import annotations

from datetime import date

from rest_framework.exceptions import ValidationError

from assessments.models import AssessmentConfig, AssessmentItemScore, GradeBand, SubjectScore
from schools.models import Term
from teachers.models import TeachingAssignment

MISSING_CONFIG_MESSAGE = (
    'Assessment setup is incomplete for this class level. '
    'Ask an admin to finish assessment configuration.'
)


def is_term_ended(term, *, today=None) -> bool:
    today = today or date.today()
    return term.end_date < today


def assert_term_editable(term):
    if is_term_ended(term):
        raise ValidationError({
            'term': (
                'Past terms are read-only. Assessment structure cannot be changed.'
            ),
        })


def get_term_assessment_config(*, level_id, term_id, required=True):
    config = (
        AssessmentConfig.objects.filter(level_id=level_id, term_id=term_id)
        .prefetch_related('grade_bands')
        .first()
    )
    if config is None and required:
        raise ValidationError({'detail': MISSING_CONFIG_MESSAGE})
    return config


def clone_assessment_config(source: AssessmentConfig, *, term) -> AssessmentConfig | None:
    existing = AssessmentConfig.objects.filter(level_id=source.level_id, term=term).first()
    if existing is not None:
        return None

    config = AssessmentConfig(
        level_id=source.level_id,
        term=term,
        continuous_assessment_weight=source.continuous_assessment_weight,
        exam_weight=source.exam_weight,
        result_type=source.result_type,
        grade_type=source.grade_type,
    )
    config.save()
    for band in source.grade_bands.all():
        GradeBand.objects.create(
            assessment_config=config,
            grade=band.grade,
            min_score=band.min_score,
            max_score=band.max_score,
            remark=band.remark,
            order=band.order,
        )
    return config


def copy_forward_assessment_configs(*, school, target_term, source_term=None):
    """Copy missing level configs onto target_term from a previous term."""
    if source_term is None:
        source_term = (
            Term.objects.filter(school=school, start_date__lt=target_term.start_date)
            .filter(assessment_configs__isnull=False)
            .distinct()
            .order_by('-start_date', '-id')
            .first()
        )
    if source_term is None or source_term.id == target_term.id:
        return []

    created = []
    sources = AssessmentConfig.objects.filter(
        term=source_term,
        level__school=school,
    ).prefetch_related('grade_bands')
    for source in sources:
        clone = clone_assessment_config(source, term=target_term)
        if clone is not None:
            created.append(clone)
    return created


def copy_forward_to_sibling_terms(*, school, source_term):
    created = []
    siblings = Term.objects.filter(academic_year_id=source_term.academic_year_id).exclude(
        id=source_term.id,
    )
    for term in siblings:
        created.extend(
            copy_forward_assessment_configs(
                school=school,
                target_term=term,
                source_term=source_term,
            )
        )
    return created


def term_has_recorded_marks(*, school, term) -> bool:
    assignment_ids = TeachingAssignment.objects.filter(
        term=term,
        class_subject__class_level__school=school,
    ).values_list('id', flat=True)
    if AssessmentItemScore.objects.filter(
        assessment_item__teaching_assignment_id__in=assignment_ids,
    ).exists():
        return True
    return SubjectScore.objects.filter(
        teaching_assignment_id__in=assignment_ids,
        exam_mark__isnull=False,
    ).exists()
