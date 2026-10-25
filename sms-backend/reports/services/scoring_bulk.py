"""Bulk published-score computation for Reports & Insights."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from assessments.models import AssessmentItem, AssessmentItemScore, AssessmentConfig, SubjectScore
from assessments.services.scoring import (
    compute_class_score,
    compute_exam_contribution,
    compute_total,
    resolve_grade,
)
from students.models import ClassEnrollment
from teachers.models import TeachingAssignment


DEFAULT_PASS_MARK = Decimal('40')


@dataclass(frozen=True)
class PublishedScoreRow:
    student_id: UUID
    teaching_assignment_id: UUID
    class_level_id: UUID
    stream_id: UUID | None
    level_id: UUID
    subject_id: UUID
    subject_name: str
    class_display_name: str
    total: Decimal
    grade: str | None


def resolve_pass_mark(config: AssessmentConfig | None) -> Decimal:
    """Pass mark from assessment settings; default 40 if unset."""
    if config is None or config.pass_mark is None:
        return DEFAULT_PASS_MARK
    return Decimal(config.pass_mark)


def _class_display_name(class_level_name: str, stream) -> str:
    if stream is None or stream.is_default:
        return class_level_name
    return f'{class_level_name} {stream.name}'


def _assignment_queryset(*, school, term, scope, class_level_id=None, level_id=None):
    qs = TeachingAssignment.objects.filter(
        term_id=term.id,
        class_subject__school=school,
        class_subject__is_active=True,
    ).select_related(
        'class_subject',
        'class_subject__subject',
        'class_subject__class_level',
        'class_subject__class_level__level',
        'stream',
    )
    if class_level_id:
        qs = qs.filter(class_subject__class_level_id=class_level_id)
    if level_id:
        qs = qs.filter(class_subject__class_level__level_id=level_id)
    if scope is not None and scope.is_scoped:
        from django.db.models import Q

        scoped = Q()
        if scope.class_subject_ids:
            scoped |= Q(class_subject_id__in=scope.class_subject_ids)
        if scope.is_class_teacher and (scope.visible_stream_ids or scope.class_level_ids):
            # Class teachers see all subjects in their streams/classes.
            if scope.visible_stream_ids:
                scoped |= Q(stream_id__in=scope.visible_stream_ids) | Q(
                    stream__isnull=True,
                    class_subject__class_level_id__in=scope.class_level_ids,
                )
            else:
                scoped |= Q(class_subject__class_level_id__in=scope.class_level_ids)
        if not scoped:
            return qs.none()
        qs = qs.filter(scoped)
    return qs


def collect_published_scores(
    *,
    school,
    term,
    scope=None,
    class_level_id=None,
    level_id=None,
) -> tuple[list[PublishedScoreRow], dict[UUID, Decimal]]:
    """Return published subject totals and pass marks keyed by level_id."""
    assignments = list(
        _assignment_queryset(
            school=school,
            term=term,
            scope=scope,
            class_level_id=class_level_id,
            level_id=level_id,
        )
    )
    if not assignments:
        return [], {}

    assignment_ids = [row.id for row in assignments]
    assignment_by_id = {row.id: row for row in assignments}

    published = list(
        SubjectScore.objects.filter(
            teaching_assignment_id__in=assignment_ids,
            is_published=True,
            exam_mark__isnull=False,
        ).only('id', 'teaching_assignment_id', 'student_id', 'exam_mark')
    )
    if not published:
        return [], {}

    student_ids = {row.student_id for row in published}
    enrollments = {
        (row.student_id, row.class_level_id): row
        for row in ClassEnrollment.objects.filter(
            term_id=term.id,
            student_id__in=student_ids,
        ).select_related('stream')
    }

    items_by_assignment: dict[UUID, list] = defaultdict(list)
    for item in AssessmentItem.objects.filter(teaching_assignment_id__in=assignment_ids):
        items_by_assignment[item.teaching_assignment_id].append(item)

    item_ids = [item.id for items in items_by_assignment.values() for item in items]
    ca_by_pair: dict[tuple[UUID, UUID], dict] = defaultdict(dict)
    if item_ids:
        for score in AssessmentItemScore.objects.filter(
            assessment_item_id__in=item_ids,
            student_id__in=student_ids,
        ).only('assessment_item_id', 'student_id', 'mark'):
            ca_by_pair[(score.student_id, score.assessment_item_id)] = score.mark

    # Rebuild as (student, assignment) → {item_id: mark}
    ca_by_student_assignment: dict[tuple[UUID, UUID], dict] = defaultdict(dict)
    item_assignment = {
        item.id: assignment_id
        for assignment_id, items in items_by_assignment.items()
        for item in items
    }
    for (student_id, item_id), mark in ca_by_pair.items():
        assignment_id = item_assignment.get(item_id)
        if assignment_id is None:
            continue
        ca_by_student_assignment[(student_id, assignment_id)][item_id] = mark

    level_ids = {
        row.class_subject.class_level.level_id for row in assignments
    }
    configs = {
        config.level_id: config
        for config in AssessmentConfig.objects.filter(
            term_id=term.id,
            level_id__in=level_ids,
        ).prefetch_related('grade_bands')
    }
    pass_marks = {
        level_id: resolve_pass_mark(configs.get(level_id))
        for level_id in level_ids
    }

    rows: list[PublishedScoreRow] = []
    for score in published:
        assignment = assignment_by_id.get(score.teaching_assignment_id)
        if assignment is None:
            continue
        class_level = assignment.class_subject.class_level
        level_id = class_level.level_id
        config = configs.get(level_id)
        if config is None:
            continue

        items = items_by_assignment.get(assignment.id, [])
        ca_raw = ca_by_student_assignment.get((score.student_id, assignment.id), {})
        class_score = compute_class_score(
            ca_raw,
            items,
            config.continuous_assessment_weight,
        )
        exam_contrib = compute_exam_contribution(score.exam_mark, config.exam_weight)
        total = compute_total(class_score, exam_contrib)
        if total is None:
            continue

        enrollment = enrollments.get((score.student_id, class_level.id))
        stream = assignment.stream
        if stream is None and enrollment is not None:
            stream = enrollment.stream
        stream_id = stream.id if stream is not None else None

        bands = list(config.grade_bands.all())
        grade = resolve_grade(total, bands) if config.uses_grades() else None

        rows.append(
            PublishedScoreRow(
                student_id=score.student_id,
                teaching_assignment_id=assignment.id,
                class_level_id=class_level.id,
                stream_id=stream_id,
                level_id=level_id,
                subject_id=assignment.class_subject.subject_id,
                subject_name=assignment.class_subject.subject.name,
                class_display_name=_class_display_name(class_level.name, stream),
                total=total,
                grade=grade,
            )
        )

    return rows, pass_marks


def student_overall_averages(rows: list[PublishedScoreRow]) -> dict[UUID, Decimal]:
    totals_by_student: dict[UUID, list[Decimal]] = defaultdict(list)
    for row in rows:
        totals_by_student[row.student_id].append(row.total)
    return {
        student_id: sum(values, Decimal('0')) / Decimal(len(values))
        for student_id, values in totals_by_student.items()
        if values
    }


def average_or_none(values: list[Decimal]) -> float | None:
    if not values:
        return None
    return float(sum(values, Decimal('0')) / Decimal(len(values)))


def pass_rate(values: list[Decimal], pass_mark: Decimal) -> float | None:
    if not values:
        return None
    passed = sum(1 for value in values if value >= pass_mark)
    return round(100.0 * passed / len(values), 1)
