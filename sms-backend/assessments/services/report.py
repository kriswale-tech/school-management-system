"""Student report card preview payload (HTML first; PDF storage later)."""

from __future__ import annotations

from decimal import Decimal

from rest_framework.exceptions import NotFound, ValidationError

from assessments.models import StudentResult
from assessments.services.term_config import get_term_assessment_config
from assessments.services.admin_overview import (
    _apply_positions,
    _assignment_contexts_for_student,
    _load_stream,
    _result_row,
    _serialize_subject_row,
    _student_full_name,
    _teacher_for_entry,
    _teacher_name,
    _class_teachers_by_key,
)
from assessments.services.scoring import compute_exam_contribution, decimal_or_none
from schools.models import Term
from students.models import ClassEnrollment
from students.services import resolve_term


def _format_report_date(value) -> str | None:
    if value is None:
        return None
    return f'{value.month}/{value.day}/{value.year}'


def _next_term_begins(*, school, term) -> str | None:
    next_term = (
        Term.objects.filter(school=school, start_date__gt=term.end_date)
        .order_by('start_date')
        .first()
    )
    if next_term is None:
        return None
    return _format_report_date(next_term.start_date)


def _term_heading(term) -> str:
    mapping = {
        'first_term': 'One',
        'second_term': 'Two',
        'third_term': 'Three',
    }
    return mapping.get(term.term, term.get_term_display())


def _format_box_address(school) -> str:
    if not school.box_address:
        return ''
    box = school.box_address.strip()
    if not box.lower().startswith('p. o.'):
        box = f'P. O. Box {box}'
    return box


def _serialize_school(school) -> dict:
    return {
        'name': school.name,
        'box_address': _format_box_address(school),
        'address': (school.address or '').strip(),
        'phone_number': (school.phone_number or '').strip(),
        'phone_number_alt': (school.phone_number_alt or '').strip(),
        'email': (school.email or '').strip(),
        'motto': school.motto or '',
        'logo_url': school.logo.url if school.logo else None,
    }


def _serialize_grade_bands(bands) -> list[dict]:
    rows = []
    for band in sorted(bands, key=lambda item: (-item.min_score, item.order, item.grade)):
        rows.append({
            'grade': band.grade,
            'min_score': band.min_score,
            'max_score': band.max_score,
            'remark': band.remark,
        })
    return rows


def _serialize_subjects_for_report(
    *,
    subject_rows,
    ca_weight,
    exam_weight,
) -> tuple[list[dict], dict]:
    subjects = []
    total_class = Decimal('0')
    total_exam = Decimal('0')
    total_overall = Decimal('0')
    weight = Decimal(str(exam_weight))
    ca_max = Decimal(str(ca_weight))

    for row in subject_rows:
        if not row['is_published'] or row['total'] is None:
            continue
        class_score = Decimal(str(row['class_score']))
        exam_contrib = compute_exam_contribution(
            Decimal(str(row['exam'])) if row['exam'] is not None else None,
            weight,
        )
        if exam_contrib is None:
            continue
        total = Decimal(str(row['total']))
        total_class += class_score
        total_exam += exam_contrib
        total_overall += total
        subjects.append({
            'subject_label': row['subject_label'],
            'class_score': float(class_score),
            'exam_score': float(exam_contrib),
            'total': float(total),
            'grade': row['grade'],
            'remark': row['band_remark'],
        })

    count = len(subjects)
    totals = {
        'class_score': decimal_or_none(total_class),
        'exam_score': decimal_or_none(total_exam),
        'total': decimal_or_none(total_overall),
        'max_class_score': decimal_or_none(ca_max * count) if count else None,
        'max_exam_score': decimal_or_none(weight * count) if count else None,
        'max_total': decimal_or_none(Decimal('100') * count) if count else None,
    }
    return subjects, totals


def get_student_report_preview(*, school, stream_id, student_id, term_id=None) -> dict:
    term = resolve_term(school, term_id)
    stream = _load_stream(school=school, stream_id=stream_id)
    class_level = stream.class_level

    enrollment = (
        ClassEnrollment.objects.filter(
            term_id=term.id,
            stream_id=stream.id,
            student_id=student_id,
        )
        .select_related('student')
        .first()
    )
    if enrollment is None:
        raise NotFound('Student not found in this class.')

    result_row = _result_row(
        student_id=student_id,
        class_level_id=class_level.id,
        stream_id=stream.id,
        term_id=term.id,
    )
    if result_row is None or result_row.status != StudentResult.Status.RELEASED:
        raise ValidationError({
            'detail': 'Reports can only be generated for released students.',
        })

    config = get_term_assessment_config(
        level_id=class_level.level_id,
        term_id=term.id,
    )
    bands = list(config.grade_bands.all())
    teacher = _teacher_for_entry(
        {'class_level_id': class_level.id, 'stream_id': stream.id},
        _class_teachers_by_key(school=school, term=term),
    )

    subject_rows = [
        _serialize_subject_row(
            ctx=ctx,
            student_id=student_id,
            config=config,
            bands=bands,
        )
        for ctx in _assignment_contexts_for_student(
            student_id=student_id,
            class_level_id=class_level.id,
            term=term,
            stream_id=stream.id,
        )
    ]
    student_payload = {
        'id': str(enrollment.student_id),
        'full_name': _student_full_name(enrollment.student),
        'student_id': enrollment.student.student_id,
        'status': 'released',
        'subjects_published_count': sum(1 for row in subject_rows if row['is_published']),
        'subjects_required_count': len(subject_rows),
        'class_teacher_remarks': result_row.remarks,
        'conduct': result_row.conduct,
        'attitude': result_row.attitude,
        'interest': result_row.interest,
        'head_teacher_remarks': result_row.head_teacher_remarks,
        'subjects': subject_rows,
    }
    _apply_positions(students=[student_payload], uses_position=config.uses_position())

    subjects, totals = _serialize_subjects_for_report(
        subject_rows=subject_rows,
        ca_weight=config.continuous_assessment_weight,
        exam_weight=config.exam_weight,
    )
    if not subjects:
        raise ValidationError({'detail': 'No published subject results to show on this report.'})

    students_on_roll = ClassEnrollment.objects.filter(
        term_id=term.id,
        stream_id=stream.id,
    ).count()

    level = class_level.level

    return {
        'student_id': str(student_id),
        'stream_id': str(stream.id),
        'term_id': str(term.id),
        'school': _serialize_school(school),
        'report_title': f"PUPIL'S REPORT SHEET: {level.name.upper()}",
        'student_name': student_payload['full_name'],
        'class_name': stream.full_name,
        'academic_year': term.academic_year.academic_year,
        'term_label': _term_heading(term),
        'next_term_begins': _next_term_begins(school=school, term=term),
        'students_on_roll': students_on_roll,
        'position': student_payload.get('overall_position'),
        'position_label': (
            _ordinal(student_payload['overall_position'])
            if student_payload.get('overall_position') is not None
            else None
        ),
        'uses_position': config.uses_position(),
        'uses_grades': config.uses_grades(),
        'weights': {
            'continuous_assessment_weight': float(config.continuous_assessment_weight),
            'exam_weight': float(config.exam_weight),
        },
        'subjects': subjects,
        'totals': totals,
        'conduct': result_row.conduct or '',
        'attitude': result_row.attitude or '',
        'interest': result_row.interest or '',
        'class_teacher_remarks': result_row.remarks or '',
        'head_teacher_remarks': result_row.head_teacher_remarks or '',
        'class_teacher_name': _teacher_name(teacher) or '',
        'grade_bands': _serialize_grade_bands(bands) if config.uses_grades() else [],
    }


def _ordinal(value: int) -> str:
    mod100 = value % 100
    if 11 <= mod100 <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(value % 10, 'th')
    return f'{value}{suffix}'
