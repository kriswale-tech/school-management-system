"""Subject Detail markbook: CA items + marks for a teaching assignment."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.db.models import Max
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from academics.services.teaching_assignments import (
    ensure_can_view_teaching_assignment,
    get_teaching_assignment,
    get_teaching_assignment_students,
)
from accounts.services.access_scope import resolve_access_scope
from assessments.models import (
    AssessmentConfig,
    AssessmentItem,
    AssessmentItemScore,
    StudentResult,
    SubjectScore,
)
from assessments.services.scoring import (
    compute_class_score,
    compute_exam_contribution,
    compute_total,
    decimal_or_none,
    resolve_grade,
    resolve_status,
)

MISSING_CONFIG_MESSAGE = (
    'Assessment setup is incomplete for this class level. '
    'Ask an admin to finish assessment configuration.'
)
CA_MARKS_REQUIRED_MESSAGE = (
    'Fill every class assessment mark before saving. Exam can wait until it is taken.'
)
ITEM_HAS_MARKS_MESSAGE = 'Cannot remove — marks already recorded for this assessment.'
MAX_MARKS_CONFLICT_MESSAGE = (
    'Some recorded marks exceed the new max. Lower those marks first, or keep a higher max.'
)
PUBLISHED_LOCK_MESSAGE = (
    'One or more students are published. Unpublish them before editing marks.'
)
NOT_COMPLETE_MESSAGE = (
    'Only students with a complete subject result (class score + exam) can be published.'
)
NOT_PUBLISHED_MESSAGE = 'Only published students can be unpublished.'
CLASS_APPROVED_MESSAGE = (
    'Cannot unpublish — the class teacher has already approved this student, '
    'or results have been released. Use the correction flow instead.'
)



def ensure_can_record_teaching_assignment(membership, assignment) -> None:
    """Assigned subject teacher, or school-wide roles (admin/staff)."""
    ensure_can_view_teaching_assignment(membership, assignment)
    scope = resolve_access_scope(membership)
    if not scope.is_scoped:
        return
    if assignment.teacher_id != membership.user_id:
        raise PermissionDenied('Only the assigned subject teacher can record assessments.')


def _get_assessment_config(assignment) -> AssessmentConfig:
    level = assignment.class_subject.class_level.level
    config = (
        AssessmentConfig.objects.filter(level_id=level.id)
        .prefetch_related('grade_bands')
        .first()
    )
    if config is None:
        raise ValidationError({'detail': MISSING_CONFIG_MESSAGE})
    return config


def _serialize_weights(config: AssessmentConfig) -> dict:
    return {
        'continuous_assessment_weight': float(config.continuous_assessment_weight),
        'exam_weight': float(config.exam_weight),
    }


def _serialize_bands(config: AssessmentConfig) -> list[dict]:
    return [
        {
            'grade': band.grade,
            'min_score': band.min_score,
            'max_score': band.max_score,
            'remark': band.remark,
            'order': band.order,
        }
        for band in config.grade_bands.all()
    ]


def _serialize_item(item: AssessmentItem) -> dict:
    return {
        'id': str(item.id),
        'name': item.name,
        'max_marks': float(item.max_marks),
        'order': item.order,
    }


def _as_uuid(value) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def get_workspace(*, school, membership, assignment_id) -> dict:
    assignment = get_teaching_assignment(school=school, assignment_id=assignment_id)
    ensure_can_view_teaching_assignment(membership, assignment)
    config = _get_assessment_config(assignment)

    students_payload = get_teaching_assignment_students(
        school=school,
        membership=membership,
        assignment_id=assignment_id,
    )
    items = list(
        AssessmentItem.objects.filter(teaching_assignment=assignment).order_by(
            'order',
            'created_at',
            'name',
        )
    )
    item_ids = [item.id for item in items]

    scores_by_student: dict = {}
    for score in AssessmentItemScore.objects.filter(assessment_item_id__in=item_ids):
        scores_by_student.setdefault(score.student_id, {})[score.assessment_item_id] = score.mark

    exam_rows = {
        row.student_id: row
        for row in SubjectScore.objects.filter(teaching_assignment=assignment)
    }

    bands = list(config.grade_bands.all())
    from assessments.models import CorrectionRequest, CorrectionRequestSubject

    correction_by_student = {
        str(row.correction_request.student_id): row.correction_request
        for row in CorrectionRequestSubject.objects.filter(
            teaching_assignment_id=assignment.id,
            correction_request__status=CorrectionRequest.Status.APPLIED,
            correction_request__school=school,
        ).select_related('correction_request')
    }

    results = []
    for student in students_payload['results']:
        student_id = student['id']
        ca_raw = scores_by_student.get(student_id, {})
        ca_payload = {
            str(item.id): decimal_or_none(ca_raw.get(item.id)) for item in items
        }
        subject_row = exam_rows.get(student_id)
        exam_mark = subject_row.exam_mark if subject_row else None
        is_published = bool(subject_row and subject_row.is_published)
        class_score = compute_class_score(
            ca_raw,
            items,
            config.continuous_assessment_weight,
        )
        exam_contrib = compute_exam_contribution(exam_mark, config.exam_weight)
        total = compute_total(class_score, exam_contrib)
        correction = correction_by_student.get(str(student_id))
        results.append({
            **student,
            'ca': ca_payload,
            'exam': decimal_or_none(exam_mark),
            'class_score': decimal_or_none(class_score),
            'exam_contribution': decimal_or_none(exam_contrib),
            'total': decimal_or_none(total),
            'grade': resolve_grade(total, bands) if config.uses_grades() else None,
            'status': resolve_status(
                class_score,
                exam_contrib,
                total,
                is_published=is_published,
            ),
            'is_published': is_published,
            'needs_correction': correction is not None and not is_published,
            'correction_reason': correction.reason if correction else '',
        })

    return {
        'term_id': str(assignment.term_id),
        'weights': _serialize_weights(config),
        'grade_bands': _serialize_bands(config),
        'result_type': config.result_type,
        'uses_grades': config.uses_grades(),
        'ca_items': [_serialize_item(item) for item in items],
        'students': results,
    }


def create_ca_item(*, school, membership, assignment_id, name: str, max_marks) -> dict:
    assignment = get_teaching_assignment(school=school, assignment_id=assignment_id)
    ensure_can_record_teaching_assignment(membership, assignment)
    _get_assessment_config(assignment)

    trimmed = (name or '').strip()
    if not trimmed:
        raise ValidationError({'name': 'Enter an assessment name.'})
    max_value = Decimal(str(max_marks))
    if max_value <= 0:
        raise ValidationError({'max_marks': 'Max marks must be greater than 0.'})

    if AssessmentItem.objects.filter(
        teaching_assignment=assignment,
        name__iexact=trimmed,
    ).exists():
        raise ValidationError({'name': 'An assessment with this name already exists.'})

    next_order = (
        AssessmentItem.objects.filter(teaching_assignment=assignment).aggregate(
            m=Max('order'),
        )['m']
        or 0
    ) + 1

    item = AssessmentItem.objects.create(
        teaching_assignment=assignment,
        name=trimmed,
        max_marks=max_value,
        order=next_order,
    )
    return _serialize_item(item)


def update_ca_item(
    *,
    school,
    membership,
    assignment_id,
    item_id,
    name: str,
    max_marks,
) -> dict:
    assignment = get_teaching_assignment(school=school, assignment_id=assignment_id)
    ensure_can_record_teaching_assignment(membership, assignment)

    item = AssessmentItem.objects.filter(
        id=item_id,
        teaching_assignment=assignment,
    ).first()
    if item is None:
        raise NotFound('Class assessment not found.')

    trimmed = (name or '').strip()
    if not trimmed:
        raise ValidationError({'name': 'Enter an assessment name.'})
    max_value = Decimal(str(max_marks))
    if max_value <= 0:
        raise ValidationError({'max_marks': 'Max marks must be greater than 0.'})

    if (
        AssessmentItem.objects.filter(teaching_assignment=assignment, name__iexact=trimmed)
        .exclude(id=item.id)
        .exists()
    ):
        raise ValidationError({'name': 'An assessment with this name already exists.'})

    if AssessmentItemScore.objects.filter(
        assessment_item=item,
        mark__gt=max_value,
    ).exists():
        raise ValidationError({'max_marks': MAX_MARKS_CONFLICT_MESSAGE})

    item.name = trimmed
    item.max_marks = max_value
    item.save()
    return _serialize_item(item)


def delete_ca_item(*, school, membership, assignment_id, item_id) -> None:
    assignment = get_teaching_assignment(school=school, assignment_id=assignment_id)
    ensure_can_record_teaching_assignment(membership, assignment)

    item = AssessmentItem.objects.filter(
        id=item_id,
        teaching_assignment=assignment,
    ).first()
    if item is None:
        raise NotFound('Class assessment not found.')

    if AssessmentItemScore.objects.filter(assessment_item=item).exists():
        raise ValidationError({'detail': ITEM_HAS_MARKS_MESSAGE})

    item.delete()


def _parse_mark(raw, *, field_label: str, max_value: Decimal) -> Decimal:
    if raw is None or raw == '':
        raise ValidationError({'detail': CA_MARKS_REQUIRED_MESSAGE})
    try:
        value = Decimal(str(raw))
    except Exception as exc:
        raise ValidationError({'detail': f'Invalid {field_label}.'}) from exc
    if value < 0 or value > max_value:
        raise ValidationError({
            'detail': f'{field_label} must be between 0 and {max_value}.',
        })
    return value


@transaction.atomic
def save_marks(*, school, membership, assignment_id, students: list[dict]) -> dict:
    assignment = get_teaching_assignment(school=school, assignment_id=assignment_id)
    ensure_can_record_teaching_assignment(membership, assignment)
    _get_assessment_config(assignment)

    items = list(AssessmentItem.objects.filter(teaching_assignment=assignment))
    if not items:
        raise ValidationError({'detail': 'Add at least one class assessment before saving.'})

    roster = get_teaching_assignment_students(
        school=school,
        membership=membership,
        assignment_id=assignment_id,
    )['results']
    roster_ids = {row['id'] for row in roster}
    if not roster_ids:
        raise ValidationError({'detail': 'No students on this subject roster.'})

    by_id = {}
    for row in students:
        sid = row.get('student_id') or row.get('id')
        if sid is None:
            continue
        by_id[_as_uuid(sid)] = row

    if not by_id:
        raise ValidationError({
            'detail': (
                'Fill every class assessment mark for at least one student before saving. '
                'Exam can wait until it is taken.'
            ),
        })

    published_ids = set(
        SubjectScore.objects.filter(
            teaching_assignment=assignment,
            is_published=True,
            student_id__in=roster_ids,
        ).values_list('student_id', flat=True)
    )

    for student_id, row in by_id.items():
        if student_id not in roster_ids:
            raise ValidationError({'detail': 'One or more students are not on this roster.'})
        if student_id in published_ids:
            raise ValidationError({
                'detail': PUBLISHED_LOCK_MESSAGE,
            })

        ca = row.get('ca') or {}
        for item in items:
            raw = ca.get(str(item.id))
            if raw is None:
                raw = ca.get(item.id)
            mark = _parse_mark(
                raw,
                field_label=item.name,
                max_value=Decimal(item.max_marks),
            )
            AssessmentItemScore.objects.update_or_create(
                assessment_item=item,
                student_id=student_id,
                defaults={'mark': mark},
            )

        exam_raw = row.get('exam', None)
        if exam_raw is None or exam_raw == '':
            SubjectScore.objects.update_or_create(
                teaching_assignment=assignment,
                student_id=student_id,
                defaults={'exam_mark': None},
            )
        else:
            exam_mark = _parse_mark(
                exam_raw,
                field_label='Exam',
                max_value=Decimal('100'),
            )
            SubjectScore.objects.update_or_create(
                teaching_assignment=assignment,
                student_id=student_id,
                defaults={'exam_mark': exam_mark},
            )

    return get_workspace(
        school=school,
        membership=membership,
        assignment_id=assignment_id,
    )


def _student_is_class_locked(*, assignment, student_id) -> bool:
    """Block subject-teacher unpublish once class teacher approved or admin released."""
    class_level_id = assignment.class_subject.class_level_id
    qs = StudentResult.objects.filter(
        student_id=student_id,
        term_id=assignment.term_id,
        class_level_id=class_level_id,
        status__in=(
            StudentResult.Status.APPROVED,
            StudentResult.Status.RELEASED,
        ),
    )
    if assignment.stream_id:
        return qs.filter(stream_id=assignment.stream_id).exists() or qs.filter(
            stream__isnull=True,
        ).exists()
    return qs.exists()


@transaction.atomic
def publish_students(*, school, membership, assignment_id, student_ids: list) -> dict:
    from django.utils import timezone

    assignment = get_teaching_assignment(school=school, assignment_id=assignment_id)
    ensure_can_record_teaching_assignment(membership, assignment)
    config = _get_assessment_config(assignment)

    if not student_ids:
        raise ValidationError({'student_ids': 'Select at least one student to publish.'})

    ids = {_as_uuid(sid) for sid in student_ids}
    roster = get_teaching_assignment_students(
        school=school,
        membership=membership,
        assignment_id=assignment_id,
    )['results']
    roster_ids = {row['id'] for row in roster}
    if not ids.issubset(roster_ids):
        raise ValidationError({'student_ids': 'One or more students are not on this roster.'})

    items = list(AssessmentItem.objects.filter(teaching_assignment=assignment))
    if not items:
        raise ValidationError({'detail': 'Add class assessments before publishing.'})

    scores_by_student: dict = {}
    for score in AssessmentItemScore.objects.filter(
        assessment_item__teaching_assignment=assignment,
        student_id__in=ids,
    ):
        scores_by_student.setdefault(score.student_id, {})[score.assessment_item_id] = score.mark

    now = timezone.now()
    for student_id in ids:
        subject_row = SubjectScore.objects.filter(
            teaching_assignment=assignment,
            student_id=student_id,
        ).first()
        exam_mark = subject_row.exam_mark if subject_row else None
        ca_raw = scores_by_student.get(student_id, {})
        class_score = compute_class_score(
            ca_raw,
            items,
            config.continuous_assessment_weight,
        )
        exam_contrib = compute_exam_contribution(exam_mark, config.exam_weight)
        total = compute_total(class_score, exam_contrib)
        status = resolve_status(
            class_score,
            exam_contrib,
            total,
            is_published=False,
        )
        if status != 'Complete':
            raise ValidationError({'detail': NOT_COMPLETE_MESSAGE})

        SubjectScore.objects.update_or_create(
            teaching_assignment=assignment,
            student_id=student_id,
            defaults={
                'exam_mark': exam_mark,
                'is_published': True,
                'published_at': now,
            },
        )

    return get_workspace(
        school=school,
        membership=membership,
        assignment_id=assignment_id,
    )


@transaction.atomic
def unpublish_students(*, school, membership, assignment_id, student_ids: list) -> dict:
    assignment = get_teaching_assignment(school=school, assignment_id=assignment_id)
    ensure_can_record_teaching_assignment(membership, assignment)

    if not student_ids:
        raise ValidationError({'student_ids': 'Select at least one student to unpublish.'})

    ids = {_as_uuid(sid) for sid in student_ids}
    for student_id in ids:
        subject_row = SubjectScore.objects.filter(
            teaching_assignment=assignment,
            student_id=student_id,
        ).first()
        if subject_row is None or not subject_row.is_published:
            raise ValidationError({'detail': NOT_PUBLISHED_MESSAGE})
        if _student_is_class_locked(assignment=assignment, student_id=student_id):
            raise ValidationError({'detail': CLASS_APPROVED_MESSAGE})
        subject_row.is_published = False
        subject_row.published_at = None
        subject_row.save(update_fields=['is_published', 'published_at', 'updated_at'])

    return get_workspace(
        school=school,
        membership=membership,
        assignment_id=assignment_id,
    )
