from collections import defaultdict

from django.db.models import Count, Prefetch, Q

from academics.models import (
    ClassStream,
    ClassSubject,
    Level,
    StudentSubjectGroup,
    SubjectGroup,
)
from students.models import ClassEnrollment
from students.services import get_active_term
from teachers.models import ClassTeacher, TeachingAssignment


def _active_streams_for_class_level(class_level):
    """Named streams if any exist; otherwise the default stream."""
    streams = [s for s in class_level.streams.all() if s.is_active]
    named = sorted(
        (s for s in streams if not s.is_default),
        key=lambda item: item.name,
    )
    if named:
        return named
    default = next((s for s in streams if s.is_default), None)
    return [default] if default is not None else []


def _iter_listed_streams(*, school):
    levels = (
        Level.objects.filter(school=school, is_active=True)
        .prefetch_related('class_levels__streams')
        .order_by('order', 'name')
    )

    for level in levels:
        class_levels = sorted(
            (cl for cl in level.class_levels.all() if cl.is_active),
            key=lambda item: (item.order, item.name),
        )
        for class_level in class_levels:
            for stream in _active_streams_for_class_level(class_level):
                yield level, class_level, stream


def _subject_slots_by_class_level(*, school):
    """Flattened subject rows per class level (groups become separate slots)."""
    class_subjects = (
        ClassSubject.objects.filter(
            school=school,
            is_active=True,
            class_level__is_active=True,
        )
        .prefetch_related(
            Prefetch(
                'groups',
                queryset=SubjectGroup.objects.filter(is_active=True).order_by('name'),
            ),
        )
    )

    slots = {}
    for class_subject in class_subjects:
        level_slots = slots.setdefault(class_subject.class_level_id, [])
        groups = list(class_subject.groups.all())
        if groups:
            for group in groups:
                level_slots.append({
                    'class_subject_id': class_subject.id,
                    'subject_group_id': group.id,
                })
        else:
            level_slots.append({
                'class_subject_id': class_subject.id,
                'subject_group_id': None,
            })
    return slots


def _teaching_coverage_maps(*, school, term):
    assignments = TeachingAssignment.objects.filter(
        term=term,
        class_subject__school=school,
    ).only('id', 'class_subject_id', 'stream_id', 'subject_group_id')

    by_group = set()
    by_stream_subject = set()
    by_whole_subject = set()

    for assignment in assignments:
        if assignment.subject_group_id:
            by_group.add(assignment.subject_group_id)
        elif assignment.stream_id:
            by_stream_subject.add((assignment.class_subject_id, assignment.stream_id))
        else:
            by_whole_subject.add(assignment.class_subject_id)

    return by_group, by_stream_subject, by_whole_subject


def _subject_slot_is_assigned(slot, *, stream_id, by_group, by_stream_subject, by_whole_subject):
    subject_group_id = slot['subject_group_id']
    if subject_group_id:
        return subject_group_id in by_group
    class_subject_id = slot['class_subject_id']
    return (
        (class_subject_id, stream_id) in by_stream_subject
        or class_subject_id in by_whole_subject
    )


def _unassigned_subject_count_for_stream(
    *,
    stream_id,
    class_level_id,
    subject_slots_by_level,
    by_group,
    by_stream_subject,
    by_whole_subject,
):
    slots = subject_slots_by_level.get(class_level_id, [])
    return sum(
        1
        for slot in slots
        if not _subject_slot_is_assigned(
            slot,
            stream_id=stream_id,
            by_group=by_group,
            by_stream_subject=by_stream_subject,
            by_whole_subject=by_whole_subject,
        )
    )


def _subject_counts_by_class_level(subject_slots_by_level):
    return {
        class_level_id: len(slots)
        for class_level_id, slots in subject_slots_by_level.items()
    }


def _student_counts_by_stream(*, school, term):
    return {
        row['id']: row['students_count']
        for row in ClassStream.objects.filter(
            class_level__school=school,
        ).annotate(
            students_count=Count(
                'enrollments',
                filter=Q(enrollments__term=term),
            ),
        ).values('id', 'students_count')
    }


def _class_teacher_maps(*, school, term):
    """Return stream-specific and whole-class teacher lookups for the term."""
    assignments = (
        ClassTeacher.objects.filter(
            term=term,
            class_level__school=school,
        )
        .select_related('teacher', 'stream')
    )

    by_stream = {}
    by_class_level = {}
    for assignment in assignments:
        teacher_payload = {
            'id': assignment.teacher_id,
            'full_name': assignment.teacher.get_full_name(),
        }
        if assignment.stream_id:
            by_stream[assignment.stream_id] = teacher_payload
        else:
            by_class_level[assignment.class_level_id] = teacher_payload

    return by_stream, by_class_level


def _resolve_class_teacher(stream, *, by_stream, by_class_level):
    return by_stream.get(stream.id) or by_class_level.get(stream.class_level_id)


def get_class_list(*, school, term=None, search=None, scope=None):
    """Flat list of class streams for the Classes page table.

    Each item is a stream: named streams become separate rows; classes with
    only a default stream appear as a single row using the class display name.
    Level refers to the department (Level), not ClassLevel.
    needs_attention is true when any subject/group lacks a teacher assignment.

    When ``scope`` is assignment-scoped (teachers), only assigned streams are
    returned.
    """
    from accounts.services.access_scope import filter_class_list_results

    term = term or get_active_term(
        school,
        detail='Set an active term before viewing classes.',
    )

    student_counts = _student_counts_by_stream(school=school, term=term)
    subject_slots_by_level = _subject_slots_by_class_level(school=school)
    subject_counts = _subject_counts_by_class_level(subject_slots_by_level)
    by_stream, by_class_level = _class_teacher_maps(school=school, term=term)
    by_group, by_stream_subject, by_whole_subject = _teaching_coverage_maps(
        school=school,
        term=term,
    )

    search_term = (search or '').strip().lower()
    results = []

    for level, class_level, stream in _iter_listed_streams(school=school):
        name = stream.full_name
        if search_term and search_term not in name.lower() and search_term not in level.name.lower():
            continue

        class_teacher = _resolve_class_teacher(
            stream,
            by_stream=by_stream,
            by_class_level=by_class_level,
        )
        unassigned_subjects = _unassigned_subject_count_for_stream(
            stream_id=stream.id,
            class_level_id=class_level.id,
            subject_slots_by_level=subject_slots_by_level,
            by_group=by_group,
            by_stream_subject=by_stream_subject,
            by_whole_subject=by_whole_subject,
        )
        results.append({
            'id': stream.id,
            'name': name,
            'level_id': level.id,
            'level_name': level.name,
            'class_level_id': class_level.id,
            'class_level_name': class_level.name,
            'students_count': student_counts.get(stream.id, 0),
            'subjects_count': subject_counts.get(class_level.id, 0),
            'unassigned_subjects_count': unassigned_subjects,
            'class_teacher': class_teacher,
            'is_default': stream.is_default,
            'is_assigned': class_teacher is not None,
            'needs_attention': unassigned_subjects > 0,
            'capacity': stream.capacity,
        })

    if scope is not None:
        results = filter_class_list_results(results, scope)

    return {
        'term_id': term.id,
        'results': results,
    }


def _teacher_payload(teacher):
    return {
        'id': teacher.id,
        'full_name': teacher.get_full_name(),
    }


def _school_teaching_assignment_maps(*, school, term):
    assignments = TeachingAssignment.objects.filter(
        term=term,
        class_subject__school=school,
    ).select_related('teacher')

    by_group = {}
    by_stream_subject = {}
    by_whole_subject = {}

    for assignment in assignments:
        payload = {
            'teacher': _teacher_payload(assignment.teacher),
            'teaching_assignment_id': assignment.id,
        }
        if assignment.subject_group_id:
            by_group[assignment.subject_group_id] = payload
        elif assignment.stream_id:
            by_stream_subject[(assignment.class_subject_id, assignment.stream_id)] = payload
        else:
            by_whole_subject[assignment.class_subject_id] = payload

    return by_group, by_stream_subject, by_whole_subject


def _resolve_pairing_teacher(
    *,
    class_subject_id,
    stream_id,
    subject_group_id,
    by_group,
    by_stream_subject,
    by_whole_subject,
):
    if subject_group_id:
        return by_group.get(subject_group_id)
    return (
        by_stream_subject.get((class_subject_id, stream_id))
        or by_whole_subject.get(class_subject_id)
    )


def _class_subjects_by_level(*, school):
    class_subjects = (
        ClassSubject.objects.filter(
            school=school,
            is_active=True,
            class_level__is_active=True,
        )
        .select_related('subject')
        .prefetch_related(
            Prefetch(
                'groups',
                queryset=SubjectGroup.objects.filter(is_active=True).order_by('name'),
            ),
        )
        .order_by('subject__name')
    )

    by_level = defaultdict(list)
    for class_subject in class_subjects:
        by_level[class_subject.class_level_id].append(class_subject)
    return by_level


def _students_by_stream(*, school, term):
    students_by_stream = defaultdict(set)
    enrollments = ClassEnrollment.objects.filter(
        term=term,
        stream__class_level__school=school,
    ).values_list('stream_id', 'student_id')
    for stream_id, student_id in enrollments:
        students_by_stream[stream_id].add(student_id)
    return students_by_stream


def _students_by_subject_group(*, school, academic_year):
    students_by_group = defaultdict(set)
    rows = StudentSubjectGroup.objects.filter(
        academic_year=academic_year,
        class_subject__school=school,
        subject_group__isnull=False,
    ).values_list('subject_group_id', 'student_id')
    for group_id, student_id in rows:
        students_by_group[group_id].add(student_id)
    return students_by_group


def get_subject_class_list(*, school, term=None, search=None, scope=None):
    """One row per subject (or subject group) taught in a class stream.

    needs_attention is true when that pairing has no students or no subject teacher.
    """
    term = term or get_active_term(
        school,
        detail='Set an active term before viewing subjects.',
    )

    students_by_stream = _students_by_stream(school=school, term=term)
    students_by_group = _students_by_subject_group(
        school=school,
        academic_year=term.academic_year,
    )
    subjects_by_level = _class_subjects_by_level(school=school)
    by_group, by_stream_subject, by_whole_subject = _school_teaching_assignment_maps(
        school=school,
        term=term,
    )

    search_term = (search or '').strip().lower()
    allowed_stream_ids = None
    if scope is not None and scope.is_scoped:
        allowed_stream_ids = set(scope.visible_stream_ids)

    results = []
    for _level, class_level, stream in _iter_listed_streams(school=school):
        if allowed_stream_ids is not None and stream.id not in allowed_stream_ids:
            continue

        stream_student_ids = students_by_stream.get(stream.id, set())
        for class_subject in subjects_by_level.get(class_level.id, []):
            groups = list(class_subject.groups.all())
            slots = groups or [None]
            for group in slots:
                assignment = _resolve_pairing_teacher(
                    class_subject_id=class_subject.id,
                    stream_id=stream.id,
                    subject_group_id=group.id if group else None,
                    by_group=by_group,
                    by_stream_subject=by_stream_subject,
                    by_whole_subject=by_whole_subject,
                )
                if group:
                    students_count = len(
                        stream_student_ids & students_by_group.get(group.id, set())
                    )
                    subject_name = class_subject.subject.name
                    group_name = group.name
                    name = f'{subject_name} ({group_name})'
                    kind = 'subject_group'
                    row_id = f'{stream.id}:{class_subject.id}:{group.id}'
                else:
                    students_count = len(stream_student_ids)
                    subject_name = class_subject.subject.name
                    group_name = None
                    name = subject_name
                    kind = 'class_subject'
                    row_id = f'{stream.id}:{class_subject.id}'

                teacher = assignment['teacher'] if assignment else None
                if search_term:
                    teacher_name = (teacher or {}).get('full_name', '')
                    haystack = ' '.join(
                        part
                        for part in (
                            subject_name,
                            group_name,
                            stream.full_name,
                            teacher_name,
                        )
                        if part
                    ).lower()
                    if search_term not in haystack:
                        continue

                results.append({
                    'id': row_id,
                    'stream_id': stream.id,
                    'class_name': stream.full_name,
                    'kind': kind,
                    'class_subject_id': class_subject.id,
                    'subject_group_id': group.id if group else None,
                    'subject_name': subject_name,
                    'group_name': group_name,
                    'name': name,
                    'students_count': students_count,
                    'teacher': teacher,
                    'teaching_assignment_id': (
                        assignment['teaching_assignment_id'] if assignment else None
                    ),
                    'needs_attention': students_count == 0 or teacher is None,
                })

    return {
        'term_id': term.id,
        'results': results,
    }


def get_class_stats(*, school, term=None, scope=None):
    """Aggregate stats over the same stream rows shown in the class list."""
    term = term or get_active_term(
        school,
        detail='Set an active term before viewing class stats.',
    )
    payload = get_class_list(school=school, term=term, scope=scope)
    results = payload['results']

    assigned_teacher_ids = {
        item['class_teacher']['id']
        for item in results
        if item['class_teacher'] is not None
    }
    empty_classes = sum(1 for item in results if item['students_count'] == 0)
    classes_with_students = len(results) - empty_classes
    total_classes = len(results)
    unassigned_classes = sum(1 for item in results if not item['is_assigned'])
    unassigned_class_subjects = sum(
        item['unassigned_subjects_count'] for item in results
    )
    total_class_subjects = sum(item['subjects_count'] for item in results)

    return {
        'term_id': term.id,
        'total_classes': total_classes,
        'total_students': sum(item['students_count'] for item in results),
        'total_teachers_assigned': len(assigned_teacher_ids),
        'unassigned_classes': unassigned_classes,
        'assigned_classes': total_classes - unassigned_classes,
        'unassigned_class_subjects': unassigned_class_subjects,
        'total_class_subjects': total_class_subjects,
        'assigned_class_subjects': max(total_class_subjects - unassigned_class_subjects, 0),
        'empty_classes': empty_classes,
        'classes_with_students': classes_with_students,
    }
