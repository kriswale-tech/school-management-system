"""School-wide assessment list and detail for admins."""

from __future__ import annotations

from uuid import UUID

from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from academics.models import ClassStream, Level
from assessments.models import StudentResult
from assessments.services.class_overview import (
    _apply_positions,
    _assignment_contexts_for_student,
    _serialize_subject_row,
    _student_full_name,
)
from schools.models import AcademicYear, Term
from students.models import ClassEnrollment
from assessments.services.term_config import get_term_assessment_config
from students.services import resolve_term
from teachers.models import ClassTeacher

ADMIN_WITH_CLASS_TEACHER = 'with_class_teacher'
ADMIN_READY = 'ready_for_you'
ADMIN_RELEASED = 'released'
ADMIN_NEEDS_CORRECTION = 'needs_correction'


def get_admin_assessment_filter_options(*, school) -> dict:
    years = (
        AcademicYear.objects.filter(school=school)
        .prefetch_related('terms')
        .order_by('-start_date')
    )
    active_term = (
        Term.objects.filter(school=school, is_active=True)
        .select_related('academic_year')
        .first()
    )
    terms = []
    for year in years:
        for term in sorted(year.terms.all(), key=lambda item: item.start_date):
            terms.append({
                'id': str(term.id),
                'label': f'{year.academic_year} · {term.get_term_display()}',
                'is_active': bool(active_term and term.id == active_term.id),
                'academic_year_id': str(year.id),
                'academic_year': year.academic_year,
            })
    return {
        'terms': terms,
        'active_term_id': str(active_term.id) if active_term else None,
    }


def list_admin_assessment_overview(*, school, term_id=None) -> dict:
    term = resolve_term(school, term_id)
    class_entries = _class_entries(school)
    teachers_by_key = _class_teachers_by_key(school=school, term=term)
    enrollments_by_stream = _enrollments_by_stream(term)
    results_by_key = _results_by_key(term)

    rows = []
    with_class_teacher = ready = released = needs_correction = 0
    classes_fully_ready = 0

    for entry in class_entries:
        teacher = _teacher_for_entry(entry, teachers_by_key)
        enrollments = enrollments_by_stream.get(entry['stream_id'], [])
        counts = {
            'with_class_teacher_count': 0,
            'ready_for_you_count': 0,
            'released_count': 0,
            'needs_correction_count': 0,
        }
        for enrollment in enrollments:
            bucket = _admin_bucket(
                student_id=enrollment.student_id,
                class_level_id=entry['class_level_id'],
                stream_id=entry['stream_id'],
                results_by_key=results_by_key,
            )
            counts[f'{bucket}_count'] += 1

        students_count = len(enrollments)
        with_class_teacher += counts['with_class_teacher_count']
        ready += counts['ready_for_you_count']
        released += counts['released_count']
        needs_correction += counts['needs_correction_count']
        if students_count and counts['ready_for_you_count'] == students_count:
            classes_fully_ready += 1

        rows.append({
            'id': str(entry['stream_id']),
            'class_level_id': str(entry['class_level_id']),
            'stream_id': str(entry['stream_id']),
            'display_name': entry['display_name'],
            'class_teacher_id': str(teacher.id) if teacher else None,
            'class_teacher_name': _teacher_name(teacher),
            'students_count': students_count,
            **counts,
        })

    from assessments.models import CorrectionRequest
    from assessments.services.corrections import list_corrections_inbox

    inbox = list_corrections_inbox(
        school=school,
        term=term,
        statuses=(CorrectionRequest.Status.OPEN,),
        kinds=(CorrectionRequest.Kind.REOPEN_REQUEST,),
    )

    return {
        'term_id': str(term.id),
        'term_label': f'{term.academic_year.academic_year} · {term.get_term_display()}',
        'with_class_teacher_count': with_class_teacher,
        'ready_for_you_count': ready,
        'released_count': released,
        'needs_correction_count': needs_correction,
        'classes_fully_ready_count': classes_fully_ready,
        'corrections_inbox_count': len(inbox),
        'corrections_inbox': inbox,
        'results': rows,
    }


def _class_entries(school) -> list[dict]:
    levels = (
        Level.objects.filter(school=school, is_active=True)
        .prefetch_related('class_levels__streams')
        .order_by('order', 'name')
    )
    entries = []
    for level in levels:
        class_levels = sorted(
            (item for item in level.class_levels.all() if item.is_active),
            key=lambda item: (item.order, item.name),
        )
        for class_level in class_levels:
            streams = [stream for stream in class_level.streams.all() if stream.is_active]
            named = sorted(
                (stream for stream in streams if not stream.is_default),
                key=lambda item: item.name,
            )
            default = next((stream for stream in streams if stream.is_default), None)
            chosen = named or ([default] if default is not None else [])
            for stream in chosen:
                entries.append({
                    'stream_id': stream.id,
                    'class_level_id': class_level.id,
                    'display_name': stream.full_name,
                    'is_named_stream': not stream.is_default,
                })
    return entries


def _class_teachers_by_key(*, school, term) -> dict:
    teachers = (
        ClassTeacher.objects.filter(term=term, class_level__school=school)
        .select_related('teacher', 'stream')
    )
    return {
        (item.class_level_id, item.stream_id): item
        for item in teachers
    }


def _teacher_for_entry(entry: dict, teachers_by_key: dict):
    exact = teachers_by_key.get((entry['class_level_id'], entry['stream_id']))
    if exact is not None:
        return exact
    return teachers_by_key.get((entry['class_level_id'], None))


def _teacher_name(class_teacher) -> str | None:
    if class_teacher is None or class_teacher.teacher_id is None:
        return None
    name = class_teacher.teacher.get_full_name().strip()
    return name or None


def _enrollments_by_stream(term) -> dict:
    grouped: dict = {}
    enrollments = ClassEnrollment.objects.filter(term_id=term.id).only(
        'id',
        'student_id',
        'stream_id',
        'class_level_id',
    )
    for enrollment in enrollments:
        grouped.setdefault(enrollment.stream_id, []).append(enrollment)
    return grouped


def _results_by_key(term) -> dict:
    rows = StudentResult.objects.filter(term_id=term.id).only(
        'student_id',
        'class_level_id',
        'stream_id',
        'status',
    )
    return {
        (row.student_id, row.class_level_id, row.stream_id): row.status
        for row in rows
    }


def _admin_bucket(*, student_id, class_level_id, stream_id, results_by_key) -> str:
    status = results_by_key.get((student_id, class_level_id, stream_id))
    if status is None:
        status = results_by_key.get((student_id, class_level_id, None))
    return _bucket_from_status(status)


def _bucket_from_status(status: str | None) -> str:
    if status == StudentResult.Status.RELEASED:
        return ADMIN_RELEASED
    if status == StudentResult.Status.APPROVED:
        return ADMIN_READY
    if status == StudentResult.Status.NEEDS_CORRECTION:
        return ADMIN_NEEDS_CORRECTION
    return ADMIN_WITH_CLASS_TEACHER


def _load_stream(*, school, stream_id):
    stream = (
        ClassStream.objects.filter(id=stream_id, class_level__school=school, is_active=True)
        .select_related('class_level', 'class_level__level')
        .first()
    )
    if stream is None:
        raise NotFound('Class not found.')
    return stream


def _result_row(*, student_id, class_level_id, stream_id, term_id):
    exact = StudentResult.objects.filter(
        student_id=student_id,
        term_id=term_id,
        class_level_id=class_level_id,
        stream_id=stream_id,
    ).first()
    if exact is not None:
        return exact
    return StudentResult.objects.filter(
        student_id=student_id,
        term_id=term_id,
        class_level_id=class_level_id,
        stream__isnull=True,
    ).first()


def _serialize_stream_assessment_students(*, school, stream, term, config, bands) -> list[dict]:
    """Serialize every enrolled student in the stream, with class positions applied."""
    class_level = stream.class_level
    enrollments = list(
        ClassEnrollment.objects.filter(term_id=term.id, stream_id=stream.id)
        .select_related('student')
        .order_by('student__last_name', 'student__first_name')
    )
    students = []
    for enrollment in enrollments:
        student = enrollment.student
        result_row = _result_row(
            student_id=student.id,
            class_level_id=class_level.id,
            stream_id=stream.id,
            term_id=term.id,
        )
        subject_rows = [
            _serialize_subject_row(
                ctx=ctx,
                student_id=student.id,
                config=config,
                bands=bands,
            )
            for ctx in _assignment_contexts_for_student(
                student_id=student.id,
                class_level_id=class_level.id,
                term=term,
                stream_id=stream.id,
            )
        ]
        students.append({
            'id': str(student.id),
            'full_name': _student_full_name(student),
            'student_id': student.student_id,
            'status': _bucket_from_status(result_row.status if result_row else None),
            'subjects_published_count': sum(1 for row in subject_rows if row['is_published']),
            'subjects_required_count': len(subject_rows),
            'class_teacher_remarks': result_row.remarks if result_row else '',
            'conduct': result_row.conduct if result_row else '',
            'attitude': result_row.attitude if result_row else '',
            'interest': result_row.interest if result_row else '',
            'head_teacher_remarks': result_row.head_teacher_remarks if result_row else '',
            'subjects': subject_rows,
            'active_correction': None,
        })

    from assessments.services.corrections import list_active_corrections_for_students

    by_student = list_active_corrections_for_students(
        school=school,
        stream_id=stream.id,
        term_id=term.id,
        student_ids=[s['id'] for s in students],
    )
    for student in students:
        student['active_correction'] = by_student.get(student['id'])

    _apply_positions(students=students, uses_position=config.uses_position())
    return students


def get_admin_assessment_detail(*, school, stream_id, term_id=None) -> dict:
    term = resolve_term(school, term_id)
    stream = _load_stream(school=school, stream_id=stream_id)
    class_level = stream.class_level
    config = get_term_assessment_config(
        level_id=class_level.level_id,
        term_id=term.id,
    )
    bands = list(config.grade_bands.all())
    teacher = _teacher_for_entry(
        {'class_level_id': class_level.id, 'stream_id': stream.id},
        _class_teachers_by_key(school=school, term=term),
    )
    students = _serialize_stream_assessment_students(
        school=school,
        stream=stream,
        term=term,
        config=config,
        bands=bands,
    )
    with_class_teacher = sum(1 for s in students if s['status'] == ADMIN_WITH_CLASS_TEACHER)
    ready = sum(1 for s in students if s['status'] == ADMIN_READY)
    released = sum(1 for s in students if s['status'] == ADMIN_RELEASED)
    needs_correction = sum(1 for s in students if s['status'] == ADMIN_NEEDS_CORRECTION)
    # Admin reviews ready/released/needs-correction. Pending stay a count only.
    # Also keep released students who have an open reopen request.
    visible_students = [
        student
        for student in students
        if student['status'] in (ADMIN_READY, ADMIN_RELEASED, ADMIN_NEEDS_CORRECTION)
        or (
            student['active_correction']
            and student['active_correction']['status'] == 'open'
            and student['active_correction']['kind'] == 'reopen_request'
        )
    ]
    pending_reopen_requests = sum(
        1
        for student in students
        if student['active_correction']
        and student['active_correction']['status'] == 'open'
        and student['active_correction']['kind'] == 'reopen_request'
    )
    return {
        'id': str(stream.id),
        'term_id': str(term.id),
        'term_label': f'{term.academic_year.academic_year} · {term.get_term_display()}',
        'display_name': stream.full_name,
        'class_teacher_name': _teacher_name(teacher),
        'with_class_teacher_count': with_class_teacher,
        'ready_for_you_count': ready,
        'released_count': released,
        'needs_correction_count': needs_correction,
        'pending_reopen_requests_count': pending_reopen_requests,
        'students_count': len(visible_students),
        'weights': {
            'continuous_assessment_weight': float(config.continuous_assessment_weight),
            'exam_weight': float(config.exam_weight),
        },
        'result_type': config.result_type,
        'uses_grades': config.uses_grades(),
        'uses_position': config.uses_position(),
        'students': visible_students,
    }


def _term_label(term) -> str:
    return f'{term.academic_year.academic_year} · {term.get_term_display()}'


def _empty_student_assessment(*, term=None, active_term=None, terms=None) -> dict:
    return {
        'term_id': str(term.id) if term else None,
        'term_label': _term_label(term) if term else None,
        'active_term_id': str(active_term.id) if active_term else None,
        'terms': terms or [],
        'enrolled': False,
        'stream_id': None,
        'display_name': None,
        'class_teacher_name': None,
        'weights': None,
        'result_type': None,
        'uses_grades': False,
        'uses_position': False,
        'student': None,
    }


def get_student_assessment_detail(*, school, student_id, term_id=None) -> dict:
    """One student's assessment for a term, with positions vs the class cohort."""
    from students.services import get_student

    student = get_student(school=school, student_id=student_id)
    enrollments = list(
        ClassEnrollment.objects.filter(student=student)
        .select_related(
            'term__academic_year',
            'stream',
            'stream__class_level',
            'class_level',
        )
        .order_by('-term__start_date', '-term__created_at')
    )
    active_term = (
        Term.objects.filter(school=school, is_active=True)
        .select_related('academic_year')
        .first()
    )

    terms = []
    seen = set()
    for enrollment in enrollments:
        enrolled_term = enrollment.term
        if enrolled_term.id in seen:
            continue
        seen.add(enrolled_term.id)
        year = enrolled_term.academic_year
        terms.append({
            'id': str(enrolled_term.id),
            'label': _term_label(enrolled_term),
            'is_active': bool(active_term and enrolled_term.id == active_term.id),
            'academic_year_id': str(year.id),
            'academic_year': year.academic_year,
        })

    if term_id:
        term = resolve_term(school, term_id)
    elif active_term and any(item.term_id == active_term.id for item in enrollments):
        term = active_term
    elif enrollments:
        term = enrollments[0].term
    else:
        return _empty_student_assessment(term=active_term, active_term=active_term, terms=terms)

    enrollment = next((item for item in enrollments if item.term_id == term.id), None)
    if enrollment is None:
        return _empty_student_assessment(term=term, active_term=active_term, terms=terms)

    stream = enrollment.stream
    class_level = enrollment.class_level
    config = get_term_assessment_config(
        level_id=class_level.level_id,
        term_id=term.id,
    )
    bands = list(config.grade_bands.all())
    teacher = _teacher_for_entry(
        {'class_level_id': class_level.id, 'stream_id': stream.id},
        _class_teachers_by_key(school=school, term=term),
    )
    students = _serialize_stream_assessment_students(
        school=school,
        stream=stream,
        term=term,
        config=config,
        bands=bands,
    )
    row = next((item for item in students if item['id'] == str(student.id)), None)
    return {
        'term_id': str(term.id),
        'term_label': _term_label(term),
        'active_term_id': str(active_term.id) if active_term else None,
        'terms': terms,
        'enrolled': True,
        'stream_id': str(stream.id),
        'display_name': stream.full_name,
        'class_teacher_name': _teacher_name(teacher),
        'weights': {
            'continuous_assessment_weight': float(config.continuous_assessment_weight),
            'exam_weight': float(config.exam_weight),
        },
        'result_type': config.result_type,
        'uses_grades': config.uses_grades(),
        'uses_position': config.uses_position(),
        'student': row,
    }


def release_admin_students(
    *,
    school,
    membership,
    stream_id,
    student_ids: list,
    remarks: str = '',
    term_id=None,
) -> dict:
    term = resolve_term(school, term_id)
    stream = _load_stream(school=school, stream_id=stream_id)
    if not student_ids:
        raise ValidationError({'student_ids': 'Select at least one student to release.'})

    ids = {UUID(str(sid)) for sid in student_ids}
    roster_ids = set(
        ClassEnrollment.objects.filter(term_id=term.id, stream_id=stream.id).values_list(
            'student_id',
            flat=True,
        )
    )
    if not ids.issubset(roster_ids):
        raise ValidationError({'student_ids': 'One or more students are not in this class.'})

    now = timezone.now()
    note = (remarks or '').strip()
    for student_id in ids:
        result_row = _result_row(
            student_id=student_id,
            class_level_id=stream.class_level_id,
            stream_id=stream.id,
            term_id=term.id,
        )
        if result_row is None or result_row.status != StudentResult.Status.APPROVED:
            if result_row is not None and result_row.status == StudentResult.Status.RELEASED:
                continue
            raise ValidationError({
                'detail': 'Only students the class teacher has approved can be released.',
            })
        result_row.status = StudentResult.Status.RELEASED
        result_row.head_teacher_remarks = note
        result_row.released_at = now
        result_row.released_by = membership.user
        result_row.save(
            update_fields=[
                'status',
                'head_teacher_remarks',
                'released_at',
                'released_by',
                'updated_at',
            ]
        )

    return get_admin_assessment_detail(
        school=school,
        stream_id=stream.id,
        term_id=term.id,
    )
