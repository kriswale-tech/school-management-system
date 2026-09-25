from collections import defaultdict

from django.db import transaction
from django.db.models import Count, Prefetch, Q
from rest_framework.exceptions import NotFound, ValidationError

from academics.models import ClassStream, ClassSubject, Level, StudentSubjectGroup, SubjectGroup
from academics.services.classes import (
    _active_streams_for_class_level,
    _iter_listed_streams,
    _subject_slots_by_class_level,
    _teaching_coverage_maps,
    _unassigned_subject_count_for_stream,
)
from accounts.models import SchoolMembership, User
from schools.services.teachers import (
    create_class_teacher_assignment,
    create_teaching_assignment,
)
from students.models import ClassEnrollment
from students.services import get_active_term
from teachers.models import ClassTeacher, TeachingAssignment


def _teacher_payload(teacher):
    if teacher is None:
        return None
    return {
        'id': teacher.id,
        'full_name': teacher.get_full_name(),
    }


def _student_full_name(student):
    parts = [student.first_name, student.other_names, student.last_name]
    return ' '.join(part for part in parts if part).strip()


def _format_class_label(class_level_name, stream):
    if stream is None or stream.is_default:
        return class_level_name
    return stream.full_name


def _join_natural(items):
    items = list(items)
    if not items:
        return ''
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f'{items[0]} and {items[1]}'
    return f'{", ".join(items[:-1])}, and {items[-1]}'


def _class_teacher_summary(assignments):
    if not assignments:
        return 'Not currently assigned as a class teacher'
    labels = [
        _format_class_label(item.class_level.name, item.stream)
        for item in assignments
    ]
    return f'class teacher of {_join_natural(labels)}'


def _teaching_summary(assignments, *, level_coverage):
    """Short description of what a teacher teaches this term.

    Ungrouped subjects collapse to the level name when the teacher covers
    every listed stream in that level that offers the subject. Partial
    coverage stays as class names. Subject groups always stay as
    "Class (Group)" because each group can have its own teacher.

    Returns ``(display, search_text)``. ``search_text`` keeps the individual
    class labels so a class name still matches after the display collapses.
    """
    if not assignments:
        empty = 'No teaching assignments yet'
        return empty, empty

    by_subject = {}
    for item in assignments:
        subject = item.class_subject.subject
        bucket = by_subject.setdefault(subject.id, {
            'name': subject.name,
            'ungrouped': [],
            'grouped_labels': [],
        })
        if item.subject_group_id:
            bucket['grouped_labels'].append(
                f'{item.class_subject.class_level.name} ({item.subject_group.name})',
            )
        else:
            bucket['ungrouped'].append(item)

    display_parts = []
    search_labels = []
    for subject_id, bucket in by_subject.items():
        labels = []
        by_level = {}
        level_order = []
        for item in bucket['ungrouped']:
            level_id = item.class_subject.class_level.level_id
            if level_id not in by_level:
                level_order.append(level_id)
                by_level[level_id] = []
            by_level[level_id].append(item)

        for level_id in level_order:
            items = by_level[level_id]
            coverage = level_coverage.get((level_id, subject_id))
            class_labels = [
                _format_class_label(item.class_subject.class_level.name, item.stream)
                for item in items
            ]
            deduped = list(dict.fromkeys(class_labels))
            search_labels.extend(deduped)

            covered = set()
            if coverage is not None:
                for item in items:
                    if item.stream_id is None:
                        covered.update(
                            coverage['class_level_stream_ids'].get(
                                item.class_subject.class_level_id,
                                (),
                            ),
                        )
                    else:
                        covered.add(item.stream_id)

            if (
                coverage is not None
                and coverage['stream_ids']
                and coverage['stream_ids'] <= covered
            ):
                labels.append(coverage['level_name'])
                search_labels.append(coverage['level_name'])
            else:
                labels.extend(deduped)

        labels.extend(bucket['grouped_labels'])
        search_labels.extend(bucket['grouped_labels'])
        if labels:
            display_parts.append(
                f'teaches {bucket["name"]} in {_join_natural(labels)}',
            )

    display = '; '.join(display_parts) if display_parts else 'No teaching assignments yet'
    search_text = f'{display} {" ".join(search_labels)}'.strip()
    return display, search_text


def _get_active_level(*, school, level_id):
    level = Level.objects.filter(
        id=level_id,
        school=school,
        is_active=True,
    ).first()
    if level is None:
        raise NotFound('Level not found.')
    return level


def _level_subject_slots(*, school, level=None):
    """Listed-stream slots for active class subjects.

    Each slot is one class stream that offers a class subject. ``grouped`` is
    true when that class subject has an active subject group; those slots are
    not assignable by level.

    Pass ``level`` to scan one level. Omit it to scan every active level,
    which the teacher summary uses to decide when to collapse.
    """
    class_subject_qs = ClassSubject.objects.filter(
        school=school,
        is_active=True,
        class_level__is_active=True,
        class_level__level__is_active=True,
    )
    if level is not None:
        class_subject_qs = class_subject_qs.filter(class_level__level=level)

    class_subjects = class_subject_qs.select_related(
        'subject',
        'class_level',
    ).prefetch_related(
        Prefetch(
            'groups',
            queryset=SubjectGroup.objects.filter(is_active=True),
        ),
    )

    by_class_level = defaultdict(list)
    for class_subject in class_subjects:
        by_class_level[class_subject.class_level_id].append(class_subject)

    if level is None:
        stream_rows = list(_iter_listed_streams(school=school))
    else:
        stream_rows = []
        class_levels = (
            level.class_levels.filter(is_active=True)
            .prefetch_related('streams')
            .order_by('order', 'name')
        )
        for class_level in class_levels:
            for stream in _active_streams_for_class_level(class_level):
                stream_rows.append((level, class_level, stream))

    slots = []
    for level_obj, class_level, stream in stream_rows:
        for class_subject in by_class_level.get(class_level.id, []):
            slots.append({
                'level': level_obj,
                'class_level': class_level,
                'stream': stream,
                'class_subject': class_subject,
                'grouped': bool(class_subject.groups.all()),
            })
    return slots


def _ungrouped_level_coverage(slots):
    """Streams that offer each ungrouped subject, keyed by level and subject."""
    coverage = {}
    for slot in slots:
        if slot['grouped']:
            continue
        key = (slot['level'].id, slot['class_subject'].subject_id)
        bucket = coverage.get(key)
        if bucket is None:
            bucket = {
                'level_name': slot['level'].name,
                'stream_ids': set(),
                'class_level_stream_ids': defaultdict(set),
            }
            coverage[key] = bucket
        bucket['stream_ids'].add(slot['stream'].id)
        bucket['class_level_stream_ids'][slot['class_level'].id].add(slot['stream'].id)
    return coverage


def _assignment_coverage_keys(*, school, term, class_subject_ids):
    """Which ungrouped slots already have a teacher this term.

    A whole-class row (no stream) covers every listed stream of that class
    subject. Stream rows cover only that stream.
    """
    if not class_subject_ids:
        return set(), set()

    rows = TeachingAssignment.objects.filter(
        term=term,
        class_subject_id__in=class_subject_ids,
        class_subject__school=school,
        subject_group__isnull=True,
    ).only('class_subject_id', 'stream_id')

    whole_class_subjects = set()
    stream_pairs = set()
    for row in rows:
        if row.stream_id is None:
            whole_class_subjects.add(row.class_subject_id)
        else:
            stream_pairs.add((row.class_subject_id, row.stream_id))
    return whole_class_subjects, stream_pairs


def _slot_has_teacher(slot, *, whole_class_subjects, stream_pairs):
    class_subject_id = slot['class_subject'].id
    if class_subject_id in whole_class_subjects:
        return True
    return (class_subject_id, slot['stream'].id) in stream_pairs


def get_stream_for_school(*, school, stream_id):
    stream = (
        ClassStream.objects.select_related(
            'class_level',
            'class_level__level',
        )
        .filter(
            id=stream_id,
            class_level__school=school,
            is_active=True,
            class_level__is_active=True,
            class_level__level__is_active=True,
        )
        .first()
    )
    if stream is None:
        raise NotFound('Class not found.')
    return stream


def _resolve_class_teacher_for_stream(*, stream, term):
    assignment = (
        ClassTeacher.objects.filter(term=term, stream=stream)
        .select_related('teacher')
        .first()
    )
    if assignment is None:
        assignment = (
            ClassTeacher.objects.filter(
                term=term,
                class_level_id=stream.class_level_id,
                stream__isnull=True,
            )
            .select_related('teacher')
            .first()
        )
    if assignment is None:
        return None, None
    return _teacher_payload(assignment.teacher), assignment.id


def get_class_detail(*, school, stream_id, term=None):
    term = term or get_active_term(
        school,
        detail='Set an active term before viewing class details.',
    )
    stream = get_stream_for_school(school=school, stream_id=stream_id)
    class_level = stream.class_level
    level = class_level.level

    students_count = ClassEnrollment.objects.filter(term=term, stream=stream).count()
    class_teacher, class_teacher_assignment_id = _resolve_class_teacher_for_stream(
        stream=stream,
        term=term,
    )

    subject_slots_by_level = _subject_slots_by_class_level(school=school)
    by_group, by_stream_subject, by_whole_subject = _teaching_coverage_maps(
        school=school,
        term=term,
    )
    unassigned_subjects = _unassigned_subject_count_for_stream(
        stream_id=stream.id,
        class_level_id=class_level.id,
        subject_slots_by_level=subject_slots_by_level,
        by_group=by_group,
        by_stream_subject=by_stream_subject,
        by_whole_subject=by_whole_subject,
    )
    subjects_count = len(subject_slots_by_level.get(class_level.id, []))

    return {
        'id': stream.id,
        'name': stream.full_name,
        'level_id': level.id,
        'level_name': level.name,
        'class_level_id': class_level.id,
        'class_level_name': class_level.name,
        'students_count': students_count,
        'subjects_count': subjects_count,
        'unassigned_subjects_count': unassigned_subjects,
        'class_teacher': class_teacher,
        'class_teacher_assignment_id': class_teacher_assignment_id,
        'is_default': stream.is_default,
        'is_assigned': class_teacher is not None,
        'needs_attention': unassigned_subjects > 0,
        'capacity': stream.capacity,
        'term_id': term.id,
    }


def get_class_students(*, school, stream_id, term=None, search=None):
    term = term or get_active_term(
        school,
        detail='Set an active term before viewing class students.',
    )
    stream = get_stream_for_school(school=school, stream_id=stream_id)

    enrollments = (
        ClassEnrollment.objects.filter(term=term, stream=stream)
        .select_related('student')
        .order_by('student__last_name', 'student__first_name')
    )

    search_term = (search or '').strip().lower()
    results = []
    for enrollment in enrollments:
        student = enrollment.student
        full_name = _student_full_name(student)
        if search_term and (
            search_term not in full_name.lower()
            and search_term not in (student.student_id or '').lower()
        ):
            continue
        results.append({
            'id': student.id,
            'full_name': full_name,
            'student_id': student.student_id,
            'admission_date': student.admission_date,
        })

    return {
        'term_id': term.id,
        'results': results,
    }


def _teaching_assignment_maps(*, class_level, term):
    assignments = (
        TeachingAssignment.objects.filter(
            term=term,
            class_subject__class_level=class_level,
        )
        .select_related('teacher', 'stream', 'subject_group', 'class_subject')
    )

    by_group = {}
    by_stream_subject = {}
    by_whole_subject = {}

    for assignment in assignments:
        teacher = _teacher_payload(assignment.teacher)
        payload = {
            'teacher': teacher,
            'teaching_assignment_id': assignment.id,
        }
        if assignment.subject_group_id:
            by_group[assignment.subject_group_id] = payload
        elif assignment.stream_id:
            by_stream_subject[(assignment.class_subject_id, assignment.stream_id)] = payload
        else:
            by_whole_subject[assignment.class_subject_id] = payload

    return by_group, by_stream_subject, by_whole_subject


def _resolve_subject_teacher(
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


def get_class_subjects(*, school, stream_id, term=None):
    """Flatten class subjects into table rows.

    Subject groups become separate rows (e.g. Ghanaian Language (Twi)).
    Class subjects without groups appear as a single row.
    """
    term = term or get_active_term(
        school,
        detail='Set an active term before viewing class subjects.',
    )
    stream = get_stream_for_school(school=school, stream_id=stream_id)
    class_level = stream.class_level
    academic_year = term.academic_year

    stream_student_ids = set(
        ClassEnrollment.objects.filter(term=term, stream=stream)
        .values_list('student_id', flat=True)
    )
    stream_students_count = len(stream_student_ids)

    group_student_counts = {
        row['subject_group_id']: row['students_count']
        for row in StudentSubjectGroup.objects.filter(
            academic_year=academic_year,
            class_subject__class_level=class_level,
            student_id__in=stream_student_ids,
        ).values('subject_group_id').annotate(students_count=Count('student_id', distinct=True))
    }

    by_group, by_stream_subject, by_whole_subject = _teaching_assignment_maps(
        class_level=class_level,
        term=term,
    )

    class_subjects = (
        ClassSubject.objects.filter(class_level=class_level, is_active=True)
        .select_related('subject')
        .prefetch_related(
            Prefetch(
                'groups',
                queryset=SubjectGroup.objects.filter(is_active=True).order_by('name'),
            ),
        )
        .order_by('subject__name')
    )

    results = []
    for class_subject in class_subjects:
        groups = list(class_subject.groups.all())
        if groups:
            for group in groups:
                assignment = _resolve_subject_teacher(
                    class_subject_id=class_subject.id,
                    stream_id=stream.id,
                    subject_group_id=group.id,
                    by_group=by_group,
                    by_stream_subject=by_stream_subject,
                    by_whole_subject=by_whole_subject,
                )
                results.append({
                    'id': group.id,
                    'kind': 'subject_group',
                    'class_subject_id': class_subject.id,
                    'subject_group_id': group.id,
                    'name': f'{class_subject.subject.name} ({group.name})',
                    'subject_name': class_subject.subject.name,
                    'group_name': group.name,
                    'students_count': group_student_counts.get(group.id, 0),
                    'teacher': assignment['teacher'] if assignment else None,
                    'teaching_assignment_id': (
                        assignment['teaching_assignment_id'] if assignment else None
                    ),
                })
            continue

        assignment = _resolve_subject_teacher(
            class_subject_id=class_subject.id,
            stream_id=stream.id,
            subject_group_id=None,
            by_group=by_group,
            by_stream_subject=by_stream_subject,
            by_whole_subject=by_whole_subject,
        )
        results.append({
            'id': class_subject.id,
            'kind': 'class_subject',
            'class_subject_id': class_subject.id,
            'subject_group_id': None,
            'name': class_subject.subject.name,
            'subject_name': class_subject.subject.name,
            'group_name': None,
            'students_count': stream_students_count,
            'teacher': assignment['teacher'] if assignment else None,
            'teaching_assignment_id': (
                assignment['teaching_assignment_id'] if assignment else None
            ),
        })

    return {
        'term_id': term.id,
        'results': results,
    }


def get_class_teacher_options(*, school, term=None, search=None):
    """Teachers available for class and subject assignment.

    ``teaching_summary`` collapses a subject to the level name when the
    teacher covers every listed stream in that level. Search still matches
    the underlying class names.
    """
    term = term or get_active_term(
        school,
        detail='Set an active term before assigning teachers.',
    )
    level_coverage = _ungrouped_level_coverage(_level_subject_slots(school=school))

    memberships = (
        SchoolMembership.objects.filter(
            school=school,
            role=User.RoleChoices.TEACHER,
            is_active=True,
        )
        .select_related('user')
        .prefetch_related(
            Prefetch(
                'user__class_teacher_assignments',
                queryset=ClassTeacher.objects.filter(term=term).select_related(
                    'class_level',
                    'stream',
                ),
            ),
            Prefetch(
                'user__teaching_assignments',
                queryset=TeachingAssignment.objects.filter(term=term).select_related(
                    'class_subject__class_level__level',
                    'class_subject__subject',
                    'stream',
                    'subject_group',
                ),
            ),
        )
        .order_by('user__last_name', 'user__first_name')
    )

    search_term = (search or '').strip().lower()
    results = []
    for membership in memberships:
        teacher = membership.user
        full_name = teacher.get_full_name()
        class_teacher_assignments = list(teacher.class_teacher_assignments.all())
        teaching_assignments = list(teacher.teaching_assignments.all())
        class_teacher_summary = _class_teacher_summary(class_teacher_assignments)
        teaching_summary, teaching_search_text = _teaching_summary(
            teaching_assignments,
            level_coverage=level_coverage,
        )

        if search_term and (
            search_term not in full_name.lower()
            and search_term not in class_teacher_summary.lower()
            and search_term not in teaching_search_text.lower()
        ):
            continue

        results.append({
            'id': teacher.id,
            'full_name': full_name,
            'class_teacher_summary': class_teacher_summary,
            'teaching_summary': teaching_summary,
        })

    return {
        'term_id': term.id,
        'results': results,
    }


def assign_class_teacher(*, school, stream_id, teacher_id):
    """Assign a class teacher to a stream for the active term.

    Replaces any existing stream-specific assignment and any whole-class
    (stream-null) assignment on the same class level, so setup-era whole-class
    rows do not stack beside the new stream assignment.
    """
    term = get_active_term(
        school,
        detail='Set an active term before assigning a class teacher.',
    )
    stream = get_stream_for_school(school=school, stream_id=stream_id)

    ClassTeacher.objects.filter(
        Q(stream=stream)
        | Q(class_level_id=stream.class_level_id, stream__isnull=True),
        term=term,
    ).delete()
    create_class_teacher_assignment(
        school,
        teacher_id=teacher_id,
        class_level_id=stream.class_level_id,
        stream_id=stream.id,
    )
    return get_class_detail(school=school, stream_id=stream.id, term=term)


def assign_subject_teacher(
    *,
    school,
    stream_id,
    teacher_id,
    class_subject_id,
    subject_group_id=None,
):
    term = get_active_term(
        school,
        detail='Set an active term before assigning a subject teacher.',
    )
    stream = get_stream_for_school(school=school, stream_id=stream_id)

    class_subject = (
        ClassSubject.objects.filter(
            id=class_subject_id,
            school=school,
            class_level_id=stream.class_level_id,
            is_active=True,
        )
        .first()
    )
    if class_subject is None:
        raise ValidationError({
            'class_subject_id': 'Subject not found for this class.',
        })

    if subject_group_id:
        group = SubjectGroup.objects.filter(
            id=subject_group_id,
            class_subject=class_subject,
            is_active=True,
        ).first()
        if group is None:
            raise ValidationError({
                'subject_group_id': 'Subject group not found for this subject.',
            })

        TeachingAssignment.objects.filter(
            term=term,
            subject_group_id=group.id,
        ).delete()
        create_teaching_assignment(
            school,
            teacher_id=teacher_id,
            class_subject_id=class_subject.id,
            stream_id=None,
            subject_group_id=group.id,
        )
    else:
        # Replace stream-specific and whole-class rows for this subject so
        # setup-era stream-null assignments do not stack with the new one.
        TeachingAssignment.objects.filter(
            Q(stream_id=stream.id) | Q(stream__isnull=True),
            term=term,
            class_subject_id=class_subject.id,
            subject_group__isnull=True,
        ).delete()
        create_teaching_assignment(
            school,
            teacher_id=teacher_id,
            class_subject_id=class_subject.id,
            stream_id=stream.id,
            subject_group_id=None,
        )

    return get_class_subjects(school=school, stream_id=stream.id, term=term)


def list_level_assignable_subjects(*, school, level_id, term=None):
    """Subjects one teacher can take across a whole level.

    Included subjects are offered as an ungrouped class subject on at least
    one listed stream in the level. Subjects that exist only as groups are
    omitted; those are assigned class by class.

    ``classes_count`` is the number of listed streams that offer the subject
    without groups. ``assigned_classes_count`` is how many of those streams
    already have a subject teacher for the term.
    """
    term = term or get_active_term(
        school,
        detail='Set an active term before assigning a subject teacher.',
    )
    level = _get_active_level(school=school, level_id=level_id)
    slots = [
        slot for slot in _level_subject_slots(school=school, level=level)
        if not slot['grouped']
    ]
    class_subject_ids = {slot['class_subject'].id for slot in slots}
    whole_class_subjects, stream_pairs = _assignment_coverage_keys(
        school=school,
        term=term,
        class_subject_ids=class_subject_ids,
    )

    by_subject = {}
    for slot in slots:
        subject = slot['class_subject'].subject
        bucket = by_subject.setdefault(subject.id, {
            'subject_id': subject.id,
            'name': subject.name,
            'slots': [],
        })
        bucket['slots'].append(slot)

    results = []
    for bucket in sorted(by_subject.values(), key=lambda item: item['name'].lower()):
        assigned = sum(
            1
            for slot in bucket['slots']
            if _slot_has_teacher(
                slot,
                whole_class_subjects=whole_class_subjects,
                stream_pairs=stream_pairs,
            )
        )
        results.append({
            'subject_id': bucket['subject_id'],
            'name': bucket['name'],
            'classes_count': len(bucket['slots']),
            'assigned_classes_count': assigned,
        })

    return {
        'level_id': level.id,
        'level_name': level.name,
        'results': results,
    }


def _unique_class_names(slots):
    names = []
    seen = set()
    for slot in slots:
        name = slot['class_level'].name
        if name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def assign_level_subject_teacher(*, school, level_id, teacher_id, subject_id):
    """Assign one teacher to a subject on every listed stream in a level.

    Writes the same per-stream teaching rows as class-by-class assignment, in
    one transaction. Streams that do not offer the subject are skipped. Class
    subjects with active groups are skipped and named in
    ``skipped_grouped_classes``. Existing teachers on the affected slots are
    replaced. A whole-class row counts as already assigned for every stream
    of that class.
    """
    term = get_active_term(
        school,
        detail='Set an active term before assigning a subject teacher.',
    )
    level = _get_active_level(school=school, level_id=level_id)
    subject_slots = [
        slot
        for slot in _level_subject_slots(school=school, level=level)
        if slot['class_subject'].subject_id == subject_id
    ]
    ungrouped = [slot for slot in subject_slots if not slot['grouped']]
    grouped = [slot for slot in subject_slots if slot['grouped']]

    if not ungrouped:
        if grouped:
            raise ValidationError({
                'subject_id': (
                    'This subject is split into groups. Assign it class by class.'
                ),
            })
        raise ValidationError({
            'subject_id': 'Subject is not offered by any class in this level.',
        })

    class_subject_ids = {slot['class_subject'].id for slot in ungrouped}
    whole_class_subjects, stream_pairs = _assignment_coverage_keys(
        school=school,
        term=term,
        class_subject_ids=class_subject_ids,
    )
    replaced_count = sum(
        1
        for slot in ungrouped
        if _slot_has_teacher(
            slot,
            whole_class_subjects=whole_class_subjects,
            stream_pairs=stream_pairs,
        )
    )

    with transaction.atomic():
        for slot in ungrouped:
            class_subject = slot['class_subject']
            stream = slot['stream']
            TeachingAssignment.objects.filter(
                Q(stream_id=stream.id) | Q(stream__isnull=True),
                term=term,
                class_subject_id=class_subject.id,
                subject_group__isnull=True,
            ).delete()
            create_teaching_assignment(
                school,
                teacher_id=teacher_id,
                class_subject_id=class_subject.id,
                stream_id=stream.id,
                subject_group_id=None,
            )

    return {
        'term_id': term.id,
        'level_id': level.id,
        'level_name': level.name,
        'subject_id': subject_id,
        'subject_name': ungrouped[0]['class_subject'].subject.name,
        'assigned_count': len(ungrouped),
        'replaced_count': replaced_count,
        'skipped_grouped_classes': _unique_class_names(grouped),
    }
