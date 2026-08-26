from collections import defaultdict

from django.db.models import Count, Prefetch, Q
from rest_framework.exceptions import NotFound, ValidationError

from academics.models import ClassStream, ClassSubject, StudentSubjectGroup, SubjectGroup
from academics.services.classes import (
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


def _teaching_summary(assignments):
    if not assignments:
        return 'No teaching assignments yet'

    by_subject = defaultdict(list)
    for item in assignments:
        subject_name = item.class_subject.subject.name
        if item.subject_group_id:
            label = f'{item.class_subject.class_level.name} ({item.subject_group.name})'
        else:
            label = _format_class_label(item.class_subject.class_level.name, item.stream)
        by_subject[subject_name].append(label)

    parts = [
        f'teaches {subject} in {_join_natural(classes)}'
        for subject, classes in by_subject.items()
    ]
    return '; '.join(parts)


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
    term = term or get_active_term(
        school,
        detail='Set an active term before assigning teachers.',
    )

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
                    'class_subject__class_level',
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
        teaching_summary = _teaching_summary(teaching_assignments)

        if search_term and (
            search_term not in full_name.lower()
            and search_term not in class_teacher_summary.lower()
            and search_term not in teaching_summary.lower()
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
