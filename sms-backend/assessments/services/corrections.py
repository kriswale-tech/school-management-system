"""Assessment correction / reject / reopen workflow with audit trail."""

from __future__ import annotations

from uuid import UUID

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from assessments.models import (
    CorrectionRequest,
    CorrectionRequestEvent,
    CorrectionRequestSubject,
    Report,
    StudentResult,
    SubjectScore,
)
from assessments.services.admin_overview import (
    _load_stream,
    _result_row,
    get_admin_assessment_detail,
)
from assessments.services.class_overview import (
    _ensure_class_teacher,
    get_class_teacher_assessment_detail,
)
from students.services import resolve_term
from teachers.models import ClassTeacher, TeachingAssignment


def _as_uuid(value) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _assignment_label(assignment: TeachingAssignment) -> str:
    subject_name = assignment.class_subject.subject.name
    group = assignment.subject_group
    if group is not None:
        return f'{subject_name} ({group.name})'
    return subject_name


def _add_event(*, request: CorrectionRequest, event_type: str, actor, detail=None):
    CorrectionRequestEvent.objects.create(
        correction_request=request,
        event_type=event_type,
        detail=detail or {},
        actor=actor,
        occurred_at=timezone.now(),
    )


def serialize_correction_request(request: CorrectionRequest) -> dict:
    subjects = [
        {
            'teaching_assignment_id': str(row.teaching_assignment_id),
            'subject_label': row.subject_label,
        }
        for row in request.subjects.all()
    ]
    return {
        'id': str(request.id),
        'kind': request.kind,
        'status': request.status,
        'reason': request.reason,
        'previous_result_status': request.previous_result_status or None,
        'student_id': str(request.student_id),
        'stream_id': str(request.stream_id),
        'term_id': str(request.term_id),
        'subjects': subjects,
        'raised_by_name': (
            request.raised_by.get_full_name() if request.raised_by_id else ''
        ),
        'raised_at': request.raised_at.isoformat() if request.raised_at else None,
        'reviewed_by_name': (
            request.reviewed_by.get_full_name() if request.reviewed_by_id else ''
        ),
        'reviewed_at': request.reviewed_at.isoformat() if request.reviewed_at else None,
        'applied_at': request.applied_at.isoformat() if request.applied_at else None,
        'resolved_at': request.resolved_at.isoformat() if request.resolved_at else None,
    }


def serialize_correction_inbox_item(request: CorrectionRequest, *, class_teacher_id=None) -> dict:
    payload = serialize_correction_request(request)
    student = request.student
    stream = request.stream
    name_parts = [student.first_name, getattr(student, 'other_names', None), student.last_name]
    student_name = ' '.join(part for part in name_parts if part).strip()
    return {
        **payload,
        'student_name': student_name,
        'student_code': student.student_id,
        'class_name': stream.full_name if stream is not None else '',
        'class_teacher_id': str(class_teacher_id) if class_teacher_id else None,
        'term_label': (
            f'{request.term.academic_year.academic_year} · {request.term.get_term_display()}'
            if request.term_id
            else None
        ),
    }


def list_corrections_inbox(
    *,
    school,
    term,
    stream_ids=None,
    statuses=None,
    kinds=None,
    class_teacher_ids_by_stream=None,
) -> list[dict]:
    qs = (
        CorrectionRequest.objects.filter(school=school, term_id=term.id)
        .select_related(
            'student',
            'stream',
            'stream__class_level',
            'term',
            'term__academic_year',
            'raised_by',
            'reviewed_by',
        )
        .prefetch_related('subjects')
        .order_by('-raised_at')
    )
    if stream_ids is not None:
        qs = qs.filter(stream_id__in=stream_ids)
    if statuses is not None:
        qs = qs.filter(status__in=statuses)
    if kinds is not None:
        qs = qs.filter(kind__in=kinds)

    class_teacher_ids_by_stream = class_teacher_ids_by_stream or {}
    return [
        serialize_correction_inbox_item(
            request,
            class_teacher_id=class_teacher_ids_by_stream.get(request.stream_id),
        )
        for request in qs
    ]


def list_subject_teacher_corrections_inbox(
    *,
    school,
    term,
    teaching_assignment_ids,
) -> tuple[list[dict], dict[str, int]]:
    """Applied corrections that still need work on the given teaching assignments.

    Returns (inbox items, needs_correction_count by teaching_assignment_id).
    A student counts when their subject result for that assignment is unpublished
    (same rule as the markbook workspace).
    """
    from assessments.models import CorrectionRequestSubject, SubjectScore

    assignment_ids = [str(item) for item in teaching_assignment_ids]
    if not assignment_ids:
        return [], {}

    subject_rows = list(
        CorrectionRequestSubject.objects.filter(
            teaching_assignment_id__in=assignment_ids,
            correction_request__school=school,
            correction_request__term_id=term.id,
            correction_request__status=CorrectionRequest.Status.APPLIED,
        ).select_related(
            'correction_request',
            'correction_request__student',
            'correction_request__stream',
            'correction_request__stream__class_level',
            'correction_request__term',
            'correction_request__term__academic_year',
            'correction_request__raised_by',
            'correction_request__reviewed_by',
            'teaching_assignment',
        )
    )
    if not subject_rows:
        return [], {assignment_id: 0 for assignment_id in assignment_ids}

    published_keys = {
        (str(row.teaching_assignment_id), str(row.student_id))
        for row in SubjectScore.objects.filter(
            teaching_assignment_id__in=assignment_ids,
            is_published=True,
            student_id__in={row.correction_request.student_id for row in subject_rows},
        ).only('teaching_assignment_id', 'student_id')
    }

    counts: dict[str, set[str]] = {assignment_id: set() for assignment_id in assignment_ids}
    inbox_by_request: dict[str, CorrectionRequest] = {}
    for row in subject_rows:
        assignment_id = str(row.teaching_assignment_id)
        student_id = str(row.correction_request.student_id)
        if (assignment_id, student_id) in published_keys:
            continue
        counts[assignment_id].add(student_id)
        request = row.correction_request
        inbox_by_request[str(request.id)] = request

    inbox = [
        serialize_correction_inbox_item(request)
        for request in sorted(
            inbox_by_request.values(),
            key=lambda item: item.raised_at,
            reverse=True,
        )
    ]
    return inbox, {assignment_id: len(students) for assignment_id, students in counts.items()}


def list_active_corrections_for_students(*, school, stream_id, term_id, student_ids):
    """Map student_id -> active correction payload (open or applied)."""
    qs = (
        CorrectionRequest.objects.filter(
            school=school,
            stream_id=stream_id,
            term_id=term_id,
            student_id__in=student_ids,
            status__in=(
                CorrectionRequest.Status.OPEN,
                CorrectionRequest.Status.APPLIED,
            ),
        )
        .select_related('raised_by', 'reviewed_by')
        .prefetch_related('subjects')
        .order_by('-raised_at')
    )
    by_student: dict[str, dict] = {}
    for request in qs:
        key = str(request.student_id)
        if key not in by_student:
            by_student[key] = serialize_correction_request(request)
    return by_student


def invalidate_student_report(*, school, stream_id, student_id, term_id, actor=None):
    report = (
        Report.objects.filter(
            school=school,
            stream_id=stream_id,
            student_id=student_id,
            term_id=term_id,
        ).first()
    )
    if report is None:
        return False
    deleted = False
    if report.file:
        try:
            report.file.delete(save=False)
        except Exception:
            report.file.name = ''
        deleted = True
    report.file = None
    report.generated_at = None
    report.generated_by = None
    report.save(update_fields=[
        'file',
        'generated_at',
        'generated_by',
        'updated_at',
    ])
    return deleted


def _load_assignments_for_stream(*, school, stream, term, teaching_assignment_ids: list):
    ids = {_as_uuid(value) for value in teaching_assignment_ids}
    if not ids:
        raise ValidationError({
            'teaching_assignment_ids': 'Select at least one subject.',
        })
    assignments = list(
        TeachingAssignment.objects.filter(
            id__in=ids,
            term_id=term.id,
            class_subject__class_level_id=stream.class_level_id,
            class_subject__class_level__school=school,
        )
        .select_related(
            'class_subject',
            'class_subject__subject',
            'subject_group',
            'stream',
        )
    )
    if len(assignments) != len(ids):
        raise ValidationError({
            'teaching_assignment_ids': 'One or more subjects are invalid for this class.',
        })
    for assignment in assignments:
        if assignment.stream_id and assignment.stream_id != stream.id:
            raise ValidationError({
                'teaching_assignment_ids': (
                    'One or more subjects do not belong to this class stream.'
                ),
            })
    return assignments


def _ensure_no_open_request(*, school, stream_id, student_id, term_id):
    if CorrectionRequest.objects.filter(
        school=school,
        stream_id=stream_id,
        student_id=student_id,
        term_id=term_id,
        status=CorrectionRequest.Status.OPEN,
    ).exists():
        raise ValidationError({
            'detail': 'A correction request is already pending admin review.',
        })


def _unpublish_assignments(*, assignments, student_id):
    unpublished = []
    for assignment in assignments:
        row = SubjectScore.objects.filter(
            teaching_assignment=assignment,
            student_id=student_id,
        ).first()
        if row is None or not row.is_published:
            raise ValidationError({
                'detail': (
                    f'Cannot send back {_assignment_label(assignment)} — '
                    'it is not published.'
                ),
            })
        row.is_published = False
        row.published_at = None
        row.save(update_fields=['is_published', 'published_at', 'updated_at'])
        unpublished.append(str(assignment.id))
    return unpublished


def _set_needs_correction(*, result_row, student_id, term, stream, actor):
    now = timezone.now()
    previous = result_row.status if result_row else ''
    defaults = {
        'status': StudentResult.Status.NEEDS_CORRECTION,
        'approved_at': None,
        'approved_by': None,
        'released_at': None,
        'released_by': None,
    }
    if result_row is None:
        result_row = StudentResult.objects.create(
            student_id=student_id,
            term_id=term.id,
            class_level_id=stream.class_level_id,
            stream_id=stream.id,
            status=StudentResult.Status.NEEDS_CORRECTION,
        )
    else:
        for key, value in defaults.items():
            setattr(result_row, key, value)
        result_row.save()
    return previous, result_row


def _apply_correction_side_effects(
    *,
    school,
    stream,
    term,
    student_id,
    assignments,
    actor,
    request: CorrectionRequest,
):
    result_row = _result_row(
        student_id=student_id,
        class_level_id=stream.class_level_id,
        stream_id=stream.id,
        term_id=term.id,
    )
    previous, result_row = _set_needs_correction(
        result_row=result_row,
        student_id=student_id,
        term=term,
        stream=stream,
        actor=actor,
    )
    request.previous_result_status = previous or request.previous_result_status
    unpublished = _unpublish_assignments(assignments=assignments, student_id=student_id)
    pdf_deleted = False
    if previous == StudentResult.Status.RELEASED or request.kind in (
        CorrectionRequest.Kind.REOPEN,
        CorrectionRequest.Kind.REOPEN_REQUEST,
    ):
        pdf_deleted = invalidate_student_report(
            school=school,
            stream_id=stream.id,
            student_id=student_id,
            term_id=term.id,
            actor=actor,
        )
    now = timezone.now()
    request.status = CorrectionRequest.Status.APPLIED
    request.applied_at = now
    request.save(update_fields=[
        'status',
        'applied_at',
        'previous_result_status',
        'updated_at',
    ])
    _add_event(
        request=request,
        event_type='applied',
        actor=actor,
        detail={
            'unpublished_teaching_assignment_ids': unpublished,
            'previous_result_status': previous,
            'pdf_deleted': pdf_deleted,
        },
    )
    if pdf_deleted:
        _add_event(
            request=request,
            event_type='pdf_deleted',
            actor=actor,
            detail={},
        )
    return request


def _create_request_with_subjects(
    *,
    school,
    stream,
    term,
    student_id,
    kind,
    reason,
    assignments,
    actor,
    status,
):
    now = timezone.now()
    request = CorrectionRequest.objects.create(
        school=school,
        student_id=student_id,
        stream=stream,
        term=term,
        kind=kind,
        status=status,
        reason=(reason or '').strip(),
        raised_by=actor,
        raised_at=now,
    )
    CorrectionRequestSubject.objects.bulk_create([
        CorrectionRequestSubject(
            correction_request=request,
            teaching_assignment=assignment,
            subject_label=_assignment_label(assignment),
        )
        for assignment in assignments
    ])
    _add_event(
        request=request,
        event_type='raised',
        actor=actor,
        detail={
            'kind': kind,
            'teaching_assignment_ids': [str(a.id) for a in assignments],
            'reason': request.reason,
        },
    )
    return request


def resolve_applied_corrections_for_student(*, school, stream_id, student_id, term_id, actor):
    now = timezone.now()
    qs = CorrectionRequest.objects.filter(
        school=school,
        stream_id=stream_id,
        student_id=student_id,
        term_id=term_id,
        status=CorrectionRequest.Status.APPLIED,
    )
    for request in qs:
        request.status = CorrectionRequest.Status.RESOLVED
        request.resolved_at = now
        request.save(update_fields=['status', 'resolved_at', 'updated_at'])
        _add_event(
            request=request,
            event_type='resolved',
            actor=actor,
            detail={'via': 'reapproved'},
        )


@transaction.atomic
def reject_or_reopen_student(
    *,
    school,
    membership,
    stream_id,
    student_id,
    teaching_assignment_ids: list,
    reason: str,
    term_id=None,
) -> dict:
    """Admin/class-teacher immediate send-back (reject) or admin reopen after release."""
    if not (reason or '').strip():
        raise ValidationError({'reason': 'A reason is required.'})

    term = resolve_term(school, term_id)
    stream = _load_stream(school=school, stream_id=stream_id)
    student_id = _as_uuid(student_id)
    _ensure_no_open_request(
        school=school,
        stream_id=stream.id,
        student_id=student_id,
        term_id=term.id,
    )
    assignments = _load_assignments_for_stream(
        school=school,
        stream=stream,
        term=term,
        teaching_assignment_ids=teaching_assignment_ids,
    )
    result_row = _result_row(
        student_id=student_id,
        class_level_id=stream.class_level_id,
        stream_id=stream.id,
        term_id=term.id,
    )
    current = result_row.status if result_row else None
    actor = membership.user

    if current == StudentResult.Status.RELEASED:
        kind = CorrectionRequest.Kind.REOPEN
    else:
        kind = CorrectionRequest.Kind.REJECT

    request = _create_request_with_subjects(
        school=school,
        stream=stream,
        term=term,
        student_id=student_id,
        kind=kind,
        reason=reason,
        assignments=assignments,
        actor=actor,
        status=CorrectionRequest.Status.OPEN,
    )
    _apply_correction_side_effects(
        school=school,
        stream=stream,
        term=term,
        student_id=student_id,
        assignments=assignments,
        actor=actor,
        request=request,
    )
    return {
        'correction': serialize_correction_request(
            CorrectionRequest.objects.prefetch_related('subjects').get(pk=request.pk)
        ),
        'detail': get_admin_assessment_detail(
            school=school,
            stream_id=stream.id,
            term_id=str(term.id),
        ),
    }


@transaction.atomic
def request_reopen_student(
    *,
    school,
    membership,
    class_teacher_id,
    student_id,
    teaching_assignment_ids: list,
    reason: str,
) -> dict:
    if not (reason or '').strip():
        raise ValidationError({'reason': 'A reason is required.'})

    term = resolve_term(school, None)
    class_teacher = (
        ClassTeacher.objects.filter(
            id=class_teacher_id,
            term=term,
            class_level__school=school,
        )
        .select_related('class_level', 'stream')
        .first()
    )
    if class_teacher is None or class_teacher.stream_id is None:
        raise NotFound('Class teacher assignment not found.')
    _ensure_class_teacher(membership, class_teacher)

    stream = class_teacher.stream
    student_id = _as_uuid(student_id)
    _ensure_no_open_request(
        school=school,
        stream_id=stream.id,
        student_id=student_id,
        term_id=term.id,
    )
    result_row = _result_row(
        student_id=student_id,
        class_level_id=stream.class_level_id,
        stream_id=stream.id,
        term_id=term.id,
    )
    if result_row is None or result_row.status != StudentResult.Status.RELEASED:
        raise ValidationError({
            'detail': 'Only released students need a reopen request. Use reject instead.',
        })

    assignments = _load_assignments_for_stream(
        school=school,
        stream=stream,
        term=term,
        teaching_assignment_ids=teaching_assignment_ids,
    )
    request = _create_request_with_subjects(
        school=school,
        stream=stream,
        term=term,
        student_id=student_id,
        kind=CorrectionRequest.Kind.REOPEN_REQUEST,
        reason=reason,
        assignments=assignments,
        actor=membership.user,
        status=CorrectionRequest.Status.OPEN,
    )
    return {
        'correction': serialize_correction_request(
            CorrectionRequest.objects.prefetch_related('subjects').get(pk=request.pk)
        ),
        'detail': get_class_teacher_assessment_detail(
            school=school,
            membership=membership,
            class_teacher_id=class_teacher.id,
        ),
    }


@transaction.atomic
def review_reopen_request(
    *,
    school,
    membership,
    stream_id,
    correction_id,
    approve: bool,
    term_id=None,
) -> dict:
    term = resolve_term(school, term_id)
    stream = _load_stream(school=school, stream_id=stream_id)
    request = (
        CorrectionRequest.objects.filter(
            id=correction_id,
            school=school,
            stream_id=stream.id,
            term_id=term.id,
            kind=CorrectionRequest.Kind.REOPEN_REQUEST,
            status=CorrectionRequest.Status.OPEN,
        )
        .prefetch_related('subjects__teaching_assignment')
        .first()
    )
    if request is None:
        raise NotFound('Correction request not found.')

    actor = membership.user
    now = timezone.now()
    request.reviewed_by = actor
    request.reviewed_at = now

    if not approve:
        request.status = CorrectionRequest.Status.DECLINED
        request.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_at'])
        _add_event(request=request, event_type='declined', actor=actor, detail={})
        return {
            'correction': serialize_correction_request(request),
            'detail': get_admin_assessment_detail(
                school=school,
                stream_id=stream.id,
                term_id=str(term.id),
            ),
        }

    assignments = [
        row.teaching_assignment
        for row in request.subjects.select_related(
            'teaching_assignment',
            'teaching_assignment__class_subject',
            'teaching_assignment__class_subject__subject',
            'teaching_assignment__subject_group',
        )
    ]
    request.save(update_fields=['reviewed_by', 'reviewed_at', 'updated_at'])
    _add_event(request=request, event_type='approved', actor=actor, detail={})
    _apply_correction_side_effects(
        school=school,
        stream=stream,
        term=term,
        student_id=request.student_id,
        assignments=assignments,
        actor=actor,
        request=request,
    )
    return {
        'correction': serialize_correction_request(
            CorrectionRequest.objects.prefetch_related('subjects').get(pk=request.pk)
        ),
        'detail': get_admin_assessment_detail(
            school=school,
            stream_id=stream.id,
            term_id=str(term.id),
        ),
    }


@transaction.atomic
def reject_class_teacher_student(
    *,
    school,
    membership,
    class_teacher_id,
    student_id,
    teaching_assignment_ids: list,
    reason: str,
) -> dict:
    """Class teacher reject before release (or while needs_correction / awaiting)."""
    if not (reason or '').strip():
        raise ValidationError({'reason': 'A reason is required.'})

    term = resolve_term(school, None)
    class_teacher = (
        ClassTeacher.objects.filter(
            id=class_teacher_id,
            term=term,
            class_level__school=school,
        )
        .select_related('class_level', 'stream')
        .first()
    )
    if class_teacher is None or class_teacher.stream_id is None:
        raise NotFound('Class teacher assignment not found.')
    _ensure_class_teacher(membership, class_teacher)

    stream = class_teacher.stream
    student_id = _as_uuid(student_id)
    result_row = _result_row(
        student_id=student_id,
        class_level_id=stream.class_level_id,
        stream_id=stream.id,
        term_id=term.id,
    )
    if result_row and result_row.status == StudentResult.Status.RELEASED:
        raise ValidationError({
            'detail': 'This student is released. Request a reopen from admin instead.',
        })

    _ensure_no_open_request(
        school=school,
        stream_id=stream.id,
        student_id=student_id,
        term_id=term.id,
    )
    assignments = _load_assignments_for_stream(
        school=school,
        stream=stream,
        term=term,
        teaching_assignment_ids=teaching_assignment_ids,
    )
    request = _create_request_with_subjects(
        school=school,
        stream=stream,
        term=term,
        student_id=student_id,
        kind=CorrectionRequest.Kind.REJECT,
        reason=reason,
        assignments=assignments,
        actor=membership.user,
        status=CorrectionRequest.Status.OPEN,
    )
    _apply_correction_side_effects(
        school=school,
        stream=stream,
        term=term,
        student_id=student_id,
        assignments=assignments,
        actor=membership.user,
        request=request,
    )
    return {
        'correction': serialize_correction_request(
            CorrectionRequest.objects.prefetch_related('subjects').get(pk=request.pk)
        ),
        'detail': get_class_teacher_assessment_detail(
            school=school,
            membership=membership,
            class_teacher_id=class_teacher.id,
        ),
    }
