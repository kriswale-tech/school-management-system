"""Class-teacher assessment overview: Pending / Awaiting approval / Approved."""

from __future__ import annotations

from decimal import Decimal

from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from academics.models import ClassSubject, StudentSubjectGroup, SubjectGroup
from accounts.services.access_scope import resolve_access_scope
from assessments.models import (
    AssessmentConfig,
    AssessmentItem,
    AssessmentItemScore,
    StudentResult,
    SubjectScore,
)
from assessments.services.ranking import average_totals, competition_ranks
from assessments.services.scoring import (
    compute_class_score,
    compute_exam_contribution,
    compute_total,
    decimal_or_none,
    resolve_grade,
)
from students.models import ClassEnrollment
from students.services import get_active_term
from teachers.models import ClassTeacher, TeachingAssignment

CLASS_STATUS_PENDING = 'pending'
CLASS_STATUS_AWAITING = 'awaiting_approval'
CLASS_STATUS_APPROVED = 'approved'


def _ensure_class_teacher(membership, class_teacher: ClassTeacher) -> None:
    scope = resolve_access_scope(membership)
    if not scope.is_scoped:
        return
    if class_teacher.teacher_id != membership.user_id:
        raise PermissionDenied('You can only manage assessments for your own classes.')


def _resolve_view_stream_id(class_teacher: ClassTeacher):
    if class_teacher.stream_id:
        return class_teacher.stream_id
    from academics.models import ClassStream

    streams = list(
        ClassStream.objects.filter(class_level_id=class_teacher.class_level_id, is_active=True)
    )
    named = sorted((s for s in streams if not s.is_default), key=lambda item: item.name)
    if named:
        return named[0].id
    default = next((s for s in streams if s.is_default), None)
    return default.id if default is not None else None


def _enrollment_qs(*, class_teacher: ClassTeacher, term):
    qs = ClassEnrollment.objects.filter(
        class_level_id=class_teacher.class_level_id,
        term_id=term.id,
    ).select_related('student')
    if class_teacher.stream_id:
        qs = qs.filter(stream_id=class_teacher.stream_id)
    return qs


def _student_full_name(student) -> str:
    parts = [student.first_name, getattr(student, 'other_names', None), student.last_name]
    return ' '.join(part for part in parts if part).strip()


def _teacher_full_name(user) -> str | None:
    if user is None:
        return None
    name = user.get_full_name().strip()
    return name or None


def _assignment_contexts_for_student(*, student_id, class_level_id, term, stream_id):
    """Return list of {class_subject, subject_group, assignment} for required subjects."""
    class_subjects = ClassSubject.objects.filter(
        class_level_id=class_level_id,
        is_active=True,
    ).select_related('subject')
    contexts = []
    for class_subject in class_subjects:
        groups = list(
            SubjectGroup.objects.filter(class_subject=class_subject, is_active=True)
        )
        if groups:
            membership = (
                StudentSubjectGroup.objects.filter(
                    student_id=student_id,
                    subject_group__class_subject=class_subject,
                    academic_year_id=term.academic_year_id,
                )
                .select_related('subject_group')
                .first()
            )
            if membership is None:
                contexts.append({
                    'class_subject': class_subject,
                    'subject_group': None,
                    'assignment': None,
                    'unplaced': True,
                })
                continue
            assignment = (
                TeachingAssignment.objects.filter(
                    class_subject=class_subject,
                    subject_group_id=membership.subject_group_id,
                    term_id=term.id,
                )
                .select_related('teacher')
                .first()
            )
            contexts.append({
                'class_subject': class_subject,
                'subject_group': membership.subject_group,
                'assignment': assignment,
                'unplaced': False,
            })
            continue

        qs = TeachingAssignment.objects.filter(
            class_subject=class_subject,
            term_id=term.id,
            subject_group__isnull=True,
        ).select_related('teacher')
        if stream_id:
            assignment = qs.filter(stream_id=stream_id).first() or qs.filter(
                stream__isnull=True,
            ).first()
        else:
            assignment = qs.filter(stream__isnull=True).first()
        contexts.append({
            'class_subject': class_subject,
            'subject_group': None,
            'assignment': assignment,
            'unplaced': False,
        })
    return contexts


def _required_teaching_assignments_for_student(*, student_id, class_level_id, term, stream_id):
    """Teaching assignments that must be published for this student."""
    return [
        ctx['assignment']
        for ctx in _assignment_contexts_for_student(
            student_id=student_id,
            class_level_id=class_level_id,
            term=term,
            stream_id=stream_id,
        )
    ]


def _subject_published(assignment, student_id) -> bool:
    if assignment is None:
        return False
    return SubjectScore.objects.filter(
        teaching_assignment=assignment,
        student_id=student_id,
        is_published=True,
    ).exists()


def _class_bucket_for_student(*, student_id, class_teacher: ClassTeacher, term) -> str:
    approved = StudentResult.objects.filter(
        student_id=student_id,
        term_id=term.id,
        class_level_id=class_teacher.class_level_id,
        status__in=(
            StudentResult.Status.APPROVED,
            StudentResult.Status.RELEASED,
        ),
    )
    if class_teacher.stream_id:
        if approved.filter(stream_id=class_teacher.stream_id).exists():
            return CLASS_STATUS_APPROVED
    elif approved.filter(stream__isnull=True).exists():
        return CLASS_STATUS_APPROVED

    stream_id = class_teacher.stream_id
    assignments = _required_teaching_assignments_for_student(
        student_id=student_id,
        class_level_id=class_teacher.class_level_id,
        term=term,
        stream_id=stream_id,
    )
    if not assignments:
        return CLASS_STATUS_PENDING

    if all(_subject_published(assignment, student_id) for assignment in assignments):
        return CLASS_STATUS_AWAITING

    return CLASS_STATUS_PENDING


def list_class_teacher_assessment_overview(*, school, membership) -> dict:
    term = get_active_term(school, detail='Set an active term before viewing assessments.')
    scope = resolve_access_scope(membership)

    qs = ClassTeacher.objects.filter(
        term=term,
        class_level__school=school,
    ).select_related('class_level', 'stream', 'teacher')
    if scope.is_scoped:
        qs = qs.filter(teacher_id=membership.user_id)

    results = []
    totals = {
        'pending_count': 0,
        'awaiting_approval_count': 0,
        'approved_count': 0,
    }

    for class_teacher in qs:
        enrollments = list(_enrollment_qs(class_teacher=class_teacher, term=term))
        pending = awaiting = approved = 0
        for enrollment in enrollments:
            bucket = _class_bucket_for_student(
                student_id=enrollment.student_id,
                class_teacher=class_teacher,
                term=term,
            )
            if bucket == CLASS_STATUS_APPROVED:
                approved += 1
            elif bucket == CLASS_STATUS_AWAITING:
                awaiting += 1
            else:
                pending += 1

        totals['pending_count'] += pending
        totals['awaiting_approval_count'] += awaiting
        totals['approved_count'] += approved

        stream = class_teacher.stream
        display_name = class_teacher.class_level.name
        if stream and not stream.is_default:
            display_name = f'{display_name} {stream.name}'

        results.append({
            'id': str(class_teacher.id),
            'class_level_id': str(class_teacher.class_level_id),
            'class_level_name': class_teacher.class_level.name,
            'stream_id': str(class_teacher.stream_id) if class_teacher.stream_id else None,
            'stream_name': (
                None
                if stream is None or stream.is_default
                else stream.name
            ),
            'display_name': display_name,
            'students_count': len(enrollments),
            'view_stream_id': (
                str(_resolve_view_stream_id(class_teacher))
                if _resolve_view_stream_id(class_teacher)
                else None
            ),
            'pending_count': pending,
            'awaiting_approval_count': awaiting,
            'approved_count': approved,
        })

    return {
        'term_id': str(term.id),
        **totals,
        'results': results,
    }


def approve_class_students(
    *,
    school,
    membership,
    class_teacher_id,
    student_ids: list,
    remarks: str = '',
    conduct: str = '',
    attitude: str = '',
    interest: str = '',
) -> dict:
    term = get_active_term(school, detail='Set an active term before approving assessments.')
    class_teacher = (
        ClassTeacher.objects.filter(
            id=class_teacher_id,
            term=term,
            class_level__school=school,
        )
        .select_related('class_level', 'stream')
        .first()
    )
    if class_teacher is None:
        raise NotFound('Class teacher assignment not found.')
    _ensure_class_teacher(membership, class_teacher)

    if not student_ids:
        raise ValidationError({'student_ids': 'Select at least one student to approve.'})

    from uuid import UUID

    ids = {UUID(str(sid)) for sid in student_ids}
    roster_ids = {
        enrollment.student_id
        for enrollment in _enrollment_qs(class_teacher=class_teacher, term=term)
    }
    if not ids.issubset(roster_ids):
        raise ValidationError({'student_ids': 'One or more students are not in this class.'})

    now = timezone.now()
    for student_id in ids:
        bucket = _class_bucket_for_student(
            student_id=student_id,
            class_teacher=class_teacher,
            term=term,
        )
        if bucket == CLASS_STATUS_APPROVED:
            continue
        if bucket != CLASS_STATUS_AWAITING:
            raise ValidationError({
                'detail': (
                    'Only students with all subjects published can be approved '
                    '(Awaiting approval).'
                ),
            })

        defaults = {
            'status': StudentResult.Status.APPROVED,
            'remarks': (remarks or '').strip(),
            'conduct': (conduct or '').strip(),
            'attitude': (attitude or '').strip(),
            'interest': (interest or '').strip(),
            'approved_at': now,
            'approved_by': membership.user,
        }
        if class_teacher.stream_id:
            StudentResult.objects.update_or_create(
                student_id=student_id,
                term_id=term.id,
                class_level_id=class_teacher.class_level_id,
                stream_id=class_teacher.stream_id,
                defaults=defaults,
            )
        else:
            StudentResult.objects.update_or_create(
                student_id=student_id,
                term_id=term.id,
                class_level_id=class_teacher.class_level_id,
                stream=None,
                defaults=defaults,
            )

    return get_class_teacher_assessment_detail(
        school=school,
        membership=membership,
        class_teacher_id=class_teacher.id,
    )


def _band_remark(total, bands) -> str | None:
    if total is None:
        return None
    from decimal import Decimal

    for band in bands:
        if Decimal(band.min_score) <= total <= Decimal(band.max_score):
            return band.remark
    return None


def _serialize_subject_row(*, ctx, student_id, config, bands) -> dict:
    class_subject = ctx['class_subject']
    subject_group = ctx['subject_group']
    assignment = ctx['assignment']
    subject_name = class_subject.subject.name
    if subject_group is not None:
        subject_label = f'{subject_name} ({subject_group.name})'
    else:
        subject_label = subject_name

    if ctx.get('unplaced'):
        return {
            'subject_label': subject_label,
            'subject_name': subject_name,
            'group_name': None,
            'teacher_name': None,
            'is_published': False,
            'status': 'Not placed',
            'class_score': None,
            'exam': None,
            'total': None,
            'grade': None,
            'band_remark': None,
            'position': None,
        }

    if assignment is None:
        return {
            'subject_label': subject_label,
            'subject_name': subject_name,
            'group_name': subject_group.name if subject_group else None,
            'teacher_name': None,
            'is_published': False,
            'status': 'No teacher',
            'class_score': None,
            'exam': None,
            'total': None,
            'grade': None,
            'band_remark': None,
            'position': None,
        }

    items = list(AssessmentItem.objects.filter(teaching_assignment=assignment))
    ca_raw = {
        score.assessment_item_id: score.mark
        for score in AssessmentItemScore.objects.filter(
            assessment_item__teaching_assignment=assignment,
            student_id=student_id,
        )
    }
    subject_row = SubjectScore.objects.filter(
        teaching_assignment=assignment,
        student_id=student_id,
    ).first()
    exam_mark = subject_row.exam_mark if subject_row else None
    is_published = bool(subject_row and subject_row.is_published)
    class_score = compute_class_score(ca_raw, items, config.continuous_assessment_weight)
    exam_contrib = compute_exam_contribution(exam_mark, config.exam_weight)
    total = compute_total(class_score, exam_contrib)
    grade = resolve_grade(total, bands) if config.uses_grades() else None

    if is_published:
        status = 'Published'
    elif total is not None:
        status = 'Complete'
    else:
        status = 'Incomplete'

    return {
        'subject_label': subject_label,
        'subject_name': subject_name,
        'group_name': subject_group.name if subject_group else None,
        'teacher_name': _teacher_full_name(assignment.teacher),
        'is_published': is_published,
        'status': status,
        'class_score': decimal_or_none(class_score),
        'exam': decimal_or_none(exam_mark),
        'total': decimal_or_none(total),
        'grade': grade,
        'band_remark': _band_remark(total, bands) if config.uses_grades() else None,
        'position': None,
    }


def _apply_positions(*, students: list[dict], uses_position: bool) -> None:
    """Attach subject and overall competition ranks when the level uses position."""
    for student in students:
        student['overall_position'] = None
        student['overall_average'] = None
        student['overall_cohort_size'] = None
        for subject in student['subjects']:
            subject['position'] = None
            subject['position_cohort_size'] = None

    if not uses_position:
        return

    by_subject: dict[str, list[tuple[str, Decimal]]] = {}
    for student in students:
        for subject in student['subjects']:
            if not subject['is_published'] or subject['total'] is None:
                continue
            by_subject.setdefault(subject['subject_label'], []).append(
                (student['id'], Decimal(str(subject['total']))),
            )

    subject_rank_maps = {
        label: competition_ranks(entries)
        for label, entries in by_subject.items()
    }
    subject_cohort_sizes = {label: len(entries) for label, entries in by_subject.items()}

    for student in students:
        for subject in student['subjects']:
            ranks = subject_rank_maps.get(subject['subject_label'])
            if ranks is None:
                continue
            position = ranks.get(student['id'])
            if position is None:
                continue
            subject['position'] = position
            subject['position_cohort_size'] = subject_cohort_sizes.get(subject['subject_label'])

    overall_entries: list[tuple[str, Decimal]] = []
    averages: dict[str, Decimal] = {}
    for student in students:
        if student['status'] not in (
            CLASS_STATUS_AWAITING,
            CLASS_STATUS_APPROVED,
            'ready_for_you',
            'released',
        ):
            continue
        published_totals = [
            Decimal(str(subject['total']))
            for subject in student['subjects']
            if subject['is_published'] and subject['total'] is not None
        ]
        avg = average_totals(published_totals)
        if avg is None:
            continue
        averages[student['id']] = avg
        overall_entries.append((student['id'], avg))

    overall_ranks = competition_ranks(overall_entries)
    cohort_size = len(overall_entries)
    for student in students:
        student_id = student['id']
        if student_id not in overall_ranks:
            continue
        student['overall_position'] = overall_ranks[student_id]
        student['overall_average'] = decimal_or_none(averages[student_id])
        student['overall_cohort_size'] = cohort_size


def get_class_teacher_assessment_detail(*, school, membership, class_teacher_id) -> dict:
    term = get_active_term(school, detail='Set an active term before viewing assessments.')
    class_teacher = (
        ClassTeacher.objects.filter(
            id=class_teacher_id,
            term=term,
            class_level__school=school,
        )
        .select_related('class_level', 'class_level__level', 'stream', 'teacher')
        .first()
    )
    if class_teacher is None:
        raise NotFound('Class teacher assignment not found.')
    _ensure_class_teacher(membership, class_teacher)

    level = class_teacher.class_level.level
    config = (
        AssessmentConfig.objects.filter(level_id=level.id)
        .prefetch_related('grade_bands')
        .first()
    )
    if config is None:
        raise ValidationError({
            'detail': (
                'Assessment setup is incomplete for this class level. '
                'Ask an admin to finish assessment configuration.'
            ),
        })
    bands = list(config.grade_bands.all())

    stream = class_teacher.stream
    display_name = class_teacher.class_level.name
    if stream and not stream.is_default:
        display_name = f'{display_name} {stream.name}'

    enrollments = list(_enrollment_qs(class_teacher=class_teacher, term=term))
    pending = awaiting = approved = 0
    students = []

    for enrollment in enrollments:
        student = enrollment.student
        bucket = _class_bucket_for_student(
            student_id=student.id,
            class_teacher=class_teacher,
            term=term,
        )
        if bucket == CLASS_STATUS_APPROVED:
            approved += 1
        elif bucket == CLASS_STATUS_AWAITING:
            awaiting += 1
        else:
            pending += 1

        contexts = _assignment_contexts_for_student(
            student_id=student.id,
            class_level_id=class_teacher.class_level_id,
            term=term,
            stream_id=class_teacher.stream_id,
        )
        subject_rows = [
            _serialize_subject_row(
                ctx=ctx,
                student_id=student.id,
                config=config,
                bands=bands,
            )
            for ctx in contexts
        ]
        published_count = sum(1 for row in subject_rows if row['is_published'])
        required_count = len(subject_rows)

        result_qs = StudentResult.objects.filter(
            student_id=student.id,
            term_id=term.id,
            class_level_id=class_teacher.class_level_id,
        )
        if class_teacher.stream_id:
            result_row = result_qs.filter(stream_id=class_teacher.stream_id).first()
        else:
            result_row = result_qs.filter(stream__isnull=True).first()

        students.append({
            'id': str(student.id),
            'full_name': _student_full_name(student),
            'student_id': student.student_id,
            'status': bucket,
            'subjects_published_count': published_count,
            'subjects_required_count': required_count,
            'class_teacher_remarks': result_row.remarks if result_row else '',
            'conduct': result_row.conduct if result_row else '',
            'attitude': result_row.attitude if result_row else '',
            'interest': result_row.interest if result_row else '',
            'subjects': subject_rows,
        })

    uses_position = config.uses_position()
    _apply_positions(students=students, uses_position=uses_position)

    return {
        'id': str(class_teacher.id),
        'term_id': str(term.id),
        'display_name': display_name,
        'class_level_name': class_teacher.class_level.name,
        'stream_name': None if stream is None or stream.is_default else stream.name,
        'class_teacher_name': _teacher_full_name(class_teacher.teacher) or '',
        'pending_count': pending,
        'awaiting_approval_count': awaiting,
        'approved_count': approved,
        'students_count': len(students),
        'weights': {
            'continuous_assessment_weight': float(config.continuous_assessment_weight),
            'exam_weight': float(config.exam_weight),
        },
        'result_type': config.result_type,
        'uses_grades': config.uses_grades(),
        'uses_position': uses_position,
        'students': students,
    }
