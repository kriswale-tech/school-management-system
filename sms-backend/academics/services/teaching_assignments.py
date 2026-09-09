"""Teaching-assignment detail and students for the subject workspace."""

from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from academics.models import StudentSubjectGroup
from accounts.services.access_scope import resolve_access_scope
from students.models import ClassEnrollment
from students.services import get_active_term
from teachers.models import TeachingAssignment

NOT_A_GROUPED_SUBJECT_MESSAGE = 'Student placement only applies to subject groups.'
ALREADY_IN_OTHER_GROUP_MESSAGE = (
    'One or more students already belong to another group. '
    'Their current group teacher must unassign them first.'
)
NOT_IN_THIS_GROUP_MESSAGE = 'One or more students are not in this subject group.'
NOT_IN_CLASS_MESSAGE = 'One or more students are not enrolled in this class.'


def _student_full_name(student):
    parts = [student.first_name, student.other_names, student.last_name]
    return ' '.join(part for part in parts if part).strip()


def _serialize_stream_name(stream) -> str | None:
    if stream is None or stream.is_default:
        return None
    return stream.name


def _display_class_name(assignment) -> str:
    class_level_name = assignment.class_subject.class_level.name
    stream_name = _serialize_stream_name(assignment.stream)
    if stream_name:
        return f'{class_level_name} {stream_name}'
    return class_level_name


def _subject_label(assignment) -> str:
    subject_name = assignment.class_subject.subject.name
    if assignment.subject_group_id:
        return f'{subject_name} ({assignment.subject_group.name})'
    return subject_name


def _resolve_view_stream_id(assignment):
    if assignment.stream_id:
        return assignment.stream_id

    from academics.models import ClassStream

    class_level_id = assignment.class_subject.class_level_id
    streams = list(
        ClassStream.objects.filter(class_level_id=class_level_id, is_active=True)
    )
    named = sorted(
        (s for s in streams if not s.is_default),
        key=lambda item: item.name,
    )
    if named:
        return named[0].id
    default = next((s for s in streams if s.is_default), None)
    return default.id if default is not None else None


def get_teaching_assignment(*, school, assignment_id) -> TeachingAssignment:
    assignment = (
        TeachingAssignment.objects.filter(
            id=assignment_id,
            class_subject__school=school,
        )
        .select_related(
            'class_subject__class_level',
            'class_subject__subject',
            'stream',
            'subject_group',
            'term',
            'term__academic_year',
            'teacher',
        )
        .first()
    )
    if assignment is None:
        raise NotFound('Teaching assignment not found.')
    return assignment


def ensure_can_view_teaching_assignment(membership, assignment: TeachingAssignment) -> None:
    """School-wide roles may view any school assignment; teachers only their own."""
    scope = resolve_access_scope(membership)
    if not scope.is_scoped:
        return
    if assignment.teacher_id != membership.user_id:
        raise PermissionDenied('You can only view subjects you teach.')


def ensure_grouped_assignment(assignment: TeachingAssignment) -> None:
    if not assignment.subject_group_id:
        raise ValidationError({'detail': NOT_A_GROUPED_SUBJECT_MESSAGE})


def _class_roster_queryset(*, assignment: TeachingAssignment):
    """Enrolled students in the assignment's class/stream (no group filter)."""
    term = assignment.term
    queryset = ClassEnrollment.objects.filter(
        term=term,
        class_level_id=assignment.class_subject.class_level_id,
    ).select_related('student')

    if assignment.stream_id:
        queryset = queryset.filter(stream_id=assignment.stream_id)

    return queryset.order_by('student__last_name', 'student__first_name')


def _enrollment_queryset(*, assignment: TeachingAssignment):
    queryset = _class_roster_queryset(assignment=assignment)

    if assignment.subject_group_id:
        student_ids = StudentSubjectGroup.objects.filter(
            academic_year_id=assignment.term.academic_year_id,
            subject_group_id=assignment.subject_group_id,
        ).values_list('student_id', flat=True)
        queryset = queryset.filter(student_id__in=student_ids)

    return queryset


def _group_memberships_by_student(*, assignment: TeachingAssignment) -> dict:
    """Map student_id -> StudentSubjectGroup for this class-subject + year."""
    return {
        row.student_id: row
        for row in StudentSubjectGroup.objects.filter(
            academic_year_id=assignment.term.academic_year_id,
            class_subject_id=assignment.class_subject_id,
        ).select_related('subject_group')
    }


def _unassigned_students_count(*, assignment: TeachingAssignment) -> int:
    if not assignment.subject_group_id:
        return 0
    memberships = _group_memberships_by_student(assignment=assignment)
    return sum(
        1
        for enrollment in _class_roster_queryset(assignment=assignment)
        if enrollment.student_id not in memberships
    )


def serialize_teaching_assignment(assignment: TeachingAssignment) -> dict:
    students_count = _enrollment_queryset(assignment=assignment).count()
    is_grouped = bool(assignment.subject_group_id)
    return {
        'id': assignment.id,
        'class_subject_id': assignment.class_subject_id,
        'class_level_id': assignment.class_subject.class_level_id,
        'class_level_name': assignment.class_subject.class_level.name,
        'subject_id': assignment.class_subject.subject_id,
        'subject_name': assignment.class_subject.subject.name,
        'subject_label': _subject_label(assignment),
        'stream_id': assignment.stream_id,
        'stream_name': _serialize_stream_name(assignment.stream),
        'subject_group_id': assignment.subject_group_id,
        'subject_group_name': (
            assignment.subject_group.name if assignment.subject_group_id else None
        ),
        'display_class_name': _display_class_name(assignment),
        'students_count': students_count,
        'unassigned_students_count': (
            _unassigned_students_count(assignment=assignment) if is_grouped else 0
        ),
        'is_grouped': is_grouped,
        'view_stream_id': _resolve_view_stream_id(assignment),
        'term_id': assignment.term_id,
    }


def get_teaching_assignment_detail(*, school, membership, assignment_id) -> dict:
    assignment = get_teaching_assignment(school=school, assignment_id=assignment_id)
    ensure_can_view_teaching_assignment(membership, assignment)
    return serialize_teaching_assignment(assignment)


def get_teaching_assignment_students(
    *,
    school,
    membership,
    assignment_id,
    search=None,
) -> dict:
    assignment = get_teaching_assignment(school=school, assignment_id=assignment_id)
    ensure_can_view_teaching_assignment(membership, assignment)

    get_active_term(
        school,
        detail='Set an active term before viewing subject students.',
    )

    search_term = (search or '').strip().lower()
    results = []
    for enrollment in _enrollment_queryset(assignment=assignment):
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
        'term_id': assignment.term_id,
        'results': results,
    }


def list_subject_group_candidates(
    *,
    school,
    membership,
    assignment_id,
    search=None,
) -> dict:
    """Class roster with placement status for Assign students UI."""
    assignment = get_teaching_assignment(school=school, assignment_id=assignment_id)
    ensure_can_view_teaching_assignment(membership, assignment)
    ensure_grouped_assignment(assignment)

    memberships = _group_memberships_by_student(assignment=assignment)
    this_group_id = assignment.subject_group_id
    search_term = (search or '').strip().lower()
    unassigned_count = _unassigned_students_count(assignment=assignment)

    results = []
    for enrollment in _class_roster_queryset(assignment=assignment):
        student = enrollment.student
        full_name = _student_full_name(student)
        if search_term and (
            search_term not in full_name.lower()
            and search_term not in (student.student_id or '').lower()
        ):
            continue

        membership_row = memberships.get(student.id)
        if membership_row is None:
            status = 'unassigned'
            current_group_id = None
            current_group_name = None
        elif membership_row.subject_group_id == this_group_id:
            status = 'this_group'
            current_group_id = membership_row.subject_group_id
            current_group_name = membership_row.subject_group.name
        else:
            status = 'other_group'
            current_group_id = membership_row.subject_group_id
            current_group_name = membership_row.subject_group.name

        results.append({
            'id': student.id,
            'full_name': full_name,
            'student_id': student.student_id,
            'status': status,
            'current_group_id': current_group_id,
            'current_group_name': current_group_name,
            'selectable': status == 'unassigned',
        })

    return {
        'term_id': assignment.term_id,
        'subject_group_id': assignment.subject_group_id,
        'subject_group_name': assignment.subject_group.name,
        'unassigned_students_count': unassigned_count,
        'results': results,
    }


def _roster_student_ids(*, assignment: TeachingAssignment) -> set:
    return set(
        _class_roster_queryset(assignment=assignment).values_list('student_id', flat=True)
    )


@transaction.atomic
def assign_students_to_subject_group(
    *,
    school,
    membership,
    assignment_id,
    student_ids: list,
) -> dict:
    """Add unassigned roster students to this teaching assignment's group."""
    assignment = get_teaching_assignment(school=school, assignment_id=assignment_id)
    ensure_can_view_teaching_assignment(membership, assignment)
    ensure_grouped_assignment(assignment)

    if not student_ids:
        raise ValidationError({'student_ids': 'Select at least one student.'})

    unique_ids = list(dict.fromkeys(student_ids))
    roster_ids = _roster_student_ids(assignment=assignment)
    missing = [sid for sid in unique_ids if sid not in roster_ids]
    if missing:
        raise ValidationError({'student_ids': NOT_IN_CLASS_MESSAGE})

    memberships = _group_memberships_by_student(assignment=assignment)
    blocked = [
        sid for sid in unique_ids
        if sid in memberships and memberships[sid].subject_group_id != assignment.subject_group_id
    ]
    if blocked:
        raise ValidationError({'student_ids': ALREADY_IN_OTHER_GROUP_MESSAGE})

    to_create = [sid for sid in unique_ids if sid not in memberships]
    academic_year = assignment.term.academic_year
    StudentSubjectGroup.objects.bulk_create([
        StudentSubjectGroup(
            student_id=student_id,
            class_subject_id=assignment.class_subject_id,
            subject_group_id=assignment.subject_group_id,
            academic_year=academic_year,
        )
        for student_id in to_create
    ])

    return serialize_teaching_assignment(assignment)


@transaction.atomic
def unassign_students_from_subject_group(
    *,
    school,
    membership,
    assignment_id,
    student_ids: list,
) -> dict:
    """Remove students from this group only (they become unassigned)."""
    assignment = get_teaching_assignment(school=school, assignment_id=assignment_id)
    ensure_can_view_teaching_assignment(membership, assignment)
    ensure_grouped_assignment(assignment)

    if not student_ids:
        raise ValidationError({'student_ids': 'Select at least one student.'})

    unique_ids = list(dict.fromkeys(student_ids))
    deleted, _ = StudentSubjectGroup.objects.filter(
        academic_year_id=assignment.term.academic_year_id,
        subject_group_id=assignment.subject_group_id,
        student_id__in=unique_ids,
    ).delete()

    if deleted == 0:
        raise ValidationError({'student_ids': NOT_IN_THIS_GROUP_MESSAGE})

    return serialize_teaching_assignment(assignment)
