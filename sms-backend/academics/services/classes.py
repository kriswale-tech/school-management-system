from django.db.models import Count, Prefetch, Q

from academics.models import ClassStream, ClassSubject, Level, SubjectGroup
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


def get_class_list(*, school, term=None, search=None):
    """Flat list of class streams for the Classes page table.

    Each item is a stream: named streams become separate rows; classes with
    only a default stream appear as a single row using the class display name.
    Level refers to the department (Level), not ClassLevel.
    needs_attention is true when any subject/group lacks a teacher assignment.
    """
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

    return {
        'term_id': term.id,
        'results': results,
    }


def get_class_stats(*, school, term=None):
    """Aggregate stats over the same stream rows shown in the class list."""
    term = term or get_active_term(
        school,
        detail='Set an active term before viewing class stats.',
    )
    payload = get_class_list(school=school, term=term)
    results = payload['results']

    assigned_teacher_ids = {
        item['class_teacher']['id']
        for item in results
        if item['class_teacher'] is not None
    }
    empty_classes = sum(1 for item in results if item['students_count'] == 0)
    classes_with_students = len(results) - empty_classes

    return {
        'term_id': term.id,
        'total_classes': len(results),
        'total_students': sum(item['students_count'] for item in results),
        'total_teachers_assigned': len(assigned_teacher_ids),
        'unassigned_classes': sum(1 for item in results if not item['is_assigned']),
        'unassigned_class_subjects': sum(
            item['unassigned_subjects_count'] for item in results
        ),
        'empty_classes': empty_classes,
        'classes_with_students': classes_with_students,
    }
