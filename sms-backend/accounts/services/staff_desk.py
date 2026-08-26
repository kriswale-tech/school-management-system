"""Staff directory helpers for the school staff list, stats, and detail pages.

These sit alongside user-management APIs without changing `/accounts/users/`
behaviour. Teacher subtype flags (class / subject) are scoped to the school's
active term when one exists.
"""

from django.db.models import BooleanField, Count, Exists, OuterRef, Q, Value

from accounts.models import Profile, User
from accounts.services.users import get_school_membership, list_school_memberships
from schools.models import Term
from teachers.models import ClassTeacher, TeachingAssignment


def _active_term_for_school(school):
    """Return the school's active term, or None when none is set."""
    return Term.objects.filter(school=school, is_active=True).first()


def annotate_teacher_assignment_flags(queryset, school):
    """Annotate memberships with active-term class/subject teacher flags.

    Non-teachers (and teachers with no active-term assignments) get False.
    When the school has no active term, both flags are False.
    """
    active_term = _active_term_for_school(school)

    if active_term is None:
        return queryset.annotate(
            is_class_teacher=Value(False, output_field=BooleanField()),
            is_subject_teacher=Value(False, output_field=BooleanField()),
        )

    class_teacher_qs = ClassTeacher.objects.filter(
        teacher_id=OuterRef('user_id'),
        term=active_term,
    )
    subject_teacher_qs = TeachingAssignment.objects.filter(
        teacher_id=OuterRef('user_id'),
        term=active_term,
    )

    return queryset.annotate(
        is_class_teacher=Exists(class_teacher_qs),
        is_subject_teacher=Exists(subject_teacher_qs),
    )


def list_staff_desk_memberships(actor):
    """Memberships the actor can manage, with teacher assignment flags."""
    queryset = list_school_memberships(actor)
    return annotate_teacher_assignment_flags(queryset, actor.school)


def get_staff_desk_membership(actor, user_id):
    """Fetch one manageable membership with teacher assignment flags."""
    membership = get_school_membership(actor.school, user_id)
    annotated = annotate_teacher_assignment_flags(
        list_school_memberships(actor).filter(pk=membership.pk),
        actor.school,
    ).first()
    return annotated or membership


def get_staff_desk_stats(queryset) -> dict:
    """Role breakdown for a (possibly filtered) staff queryset.

    Search and role filters on the desk list also apply here so the cards match
    the table. `total_staff` counts every matching membership; role buckets only
    count their respective roles within that same filtered set.
    """
    aggregates = queryset.aggregate(
        total_staff=Count('id'),
        teachers=Count('id', filter=Q(role=User.RoleChoices.TEACHER)),
        accountants=Count('id', filter=Q(role=User.RoleChoices.ACCOUNTANT)),
        admins=Count('id', filter=Q(role=User.RoleChoices.ADMIN)),
    )
    return {
        'total_staff': aggregates['total_staff'] or 0,
        'teachers': aggregates['teachers'] or 0,
        'accountants': aggregates['accountants'] or 0,
        'admins': aggregates['admins'] or 0,
    }


def _serialize_profile(user) -> dict | None:
    try:
        profile = user.profile
    except Profile.DoesNotExist:
        return None

    return {
        'profile_picture': profile.profile_picture.url if profile.profile_picture else None,
        'bio': profile.bio,
        'date_of_birth': profile.date_of_birth,
        'gender': profile.gender,
        'address': profile.address,
        'phone_number_alt': profile.phone_number_alt,
    }


def _serialize_stream_name(stream) -> str | None:
    if stream is None or stream.is_default:
        return None
    return stream.name


def _profile_picture_url(user) -> str | None:
    try:
        picture = user.profile.profile_picture
    except Profile.DoesNotExist:
        return None
    return picture.url if picture else None


def serialize_staff_desk_row(membership) -> dict:
    """Compact row for the staff directory table."""
    user = membership.user
    role = membership.role
    is_teacher = role == User.RoleChoices.TEACHER

    return {
        'id': user.id,
        'membership_id': membership.id,
        'full_name': user.get_full_name(),
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email or None,
        'phone_number': user.phone_number,
        'role': role,
        'is_active': membership.is_active,
        'date_added': membership.created_at,
        'profile_picture': _profile_picture_url(user),
        # Teacher subtypes only apply when the membership role is teacher.
        'is_class_teacher': bool(getattr(membership, 'is_class_teacher', False)) if is_teacher else False,
        'is_subject_teacher': (
            bool(getattr(membership, 'is_subject_teacher', False)) if is_teacher else False
        ),
    }


def _enrollment_count(*, term, class_level_id, stream_id=None) -> int:
    """Students enrolled in a stream, or in every stream of a class level."""
    from students.models import ClassEnrollment

    queryset = ClassEnrollment.objects.filter(term=term)
    if stream_id:
        return queryset.filter(stream_id=stream_id).count()
    return queryset.filter(class_level_id=class_level_id).count()


def _subject_group_student_count(*, term, subject_group_id, class_level_id, stream_id=None) -> int:
    """Students in a subject group, limited to the assignment's class/stream."""
    from academics.models import StudentSubjectGroup
    from students.models import ClassEnrollment

    enrollment_qs = ClassEnrollment.objects.filter(term=term, class_level_id=class_level_id)
    if stream_id:
        enrollment_qs = enrollment_qs.filter(stream_id=stream_id)

    return (
        StudentSubjectGroup.objects.filter(
            academic_year_id=term.academic_year_id,
            subject_group_id=subject_group_id,
            student_id__in=enrollment_qs.values('student_id'),
        )
        .values('student_id')
        .distinct()
        .count()
    )


def _class_teacher_display_name(assignment) -> str:
    if assignment.stream_id:
        return assignment.stream.full_name
    return assignment.class_level.name


def _teaching_display_class_name(assignment) -> str:
    class_level_name = assignment.class_subject.class_level.name
    stream_name = _serialize_stream_name(assignment.stream)
    if stream_name:
        return f'{class_level_name} {stream_name}'
    return class_level_name


def serialize_staff_desk_detail(membership) -> dict:
    """Full staff member payload for the details page."""
    user = membership.user
    school = membership.school
    row = serialize_staff_desk_row(membership)
    active_term = _active_term_for_school(school)

    class_teacher_assignments = []
    teaching_assignments = []

    if membership.role == User.RoleChoices.TEACHER and active_term is not None:
        for assignment in ClassTeacher.objects.filter(
            teacher=user,
            term=active_term,
        ).select_related('class_level', 'stream'):
            class_teacher_assignments.append({
                'id': assignment.id,
                'class_level_id': assignment.class_level_id,
                'class_level_name': assignment.class_level.name,
                'stream_id': assignment.stream_id,
                'stream_name': _serialize_stream_name(assignment.stream),
                'display_name': _class_teacher_display_name(assignment),
                'students_count': _enrollment_count(
                    term=active_term,
                    class_level_id=assignment.class_level_id,
                    stream_id=assignment.stream_id,
                ),
            })

        for assignment in TeachingAssignment.objects.filter(
            teacher=user,
            term=active_term,
        ).select_related(
            'class_subject__class_level',
            'class_subject__subject',
            'stream',
            'subject_group',
        ):
            class_level_id = assignment.class_subject.class_level_id
            if assignment.subject_group_id:
                students_count = _subject_group_student_count(
                    term=active_term,
                    subject_group_id=assignment.subject_group_id,
                    class_level_id=class_level_id,
                    stream_id=assignment.stream_id,
                )
            else:
                students_count = _enrollment_count(
                    term=active_term,
                    class_level_id=class_level_id,
                    stream_id=assignment.stream_id,
                )

            teaching_assignments.append({
                'id': assignment.id,
                'class_subject_id': assignment.class_subject_id,
                'class_level_id': class_level_id,
                'class_level_name': assignment.class_subject.class_level.name,
                'subject_id': assignment.class_subject.subject_id,
                'subject_name': assignment.class_subject.subject.name,
                'stream_id': assignment.stream_id,
                'stream_name': _serialize_stream_name(assignment.stream),
                'subject_group_id': assignment.subject_group_id,
                'subject_group_name': (
                    assignment.subject_group.name if assignment.subject_group_id else None
                ),
                'display_class_name': _teaching_display_class_name(assignment),
                'students_count': students_count,
            })

    return {
        **row,
        'profile': _serialize_profile(user),
        'school_id': school.id,
        'school_setup_completed': school.setup_completed,
        'class_teacher_assignments': class_teacher_assignments,
        'teaching_assignments': teaching_assignments,
    }
