"""Write and list school activity feed rows."""

from django.db.models import Q

from activities.models import Activity

# Events about a class as a whole. Subject teachers on that class see these.
# Subject-specific rows are matched through teaching_assignment instead.
CLASS_WIDE_VERBS = (
    Activity.Verb.STUDENTS_APPROVED,
    Activity.Verb.REPORTS_RELEASED,
    Activity.Verb.CLASS_TEACHER_ASSIGNED,
)

FEE_VERBS = (
    Activity.Verb.PAYMENT_RECORDED,
    Activity.Verb.ADVANCE_CREATED,
    Activity.Verb.FEE_STRUCTURE_PUBLISHED,
    Activity.Verb.FEE_STRUCTURE_APPLIED,
)


def record_activity(
    *,
    school,
    verb,
    summary,
    href='',
    actor=None,
    term=None,
    target_kind='',
    target_id=None,
    stream=None,
    teaching_assignment=None,
):
    """Insert one feed row. Call this inside the action's transaction."""
    actor_name = ''
    if actor is not None:
        actor_name = (actor.get_full_name() or '').strip()

    return Activity.objects.create(
        school=school,
        actor=actor,
        actor_name=actor_name,
        verb=verb,
        summary=summary,
        href=href or '',
        term=term,
        target_kind=target_kind or '',
        target_id=target_id,
        stream=stream,
        teaching_assignment=teaching_assignment,
    )


def list_activities(*, school, term=None):
    queryset = Activity.objects.filter(school=school)
    if term is not None:
        queryset = queryset.filter(term=term)
    return queryset.order_by('-created_at')


def list_activities_for_accountant(*, school, term=None):
    """Fee desk events only — payments, advances, catalog publish/apply."""
    return list_activities(school=school, term=term).filter(verb__in=FEE_VERBS)


def list_activities_for_staff(*, school, term=None):
    """Academics, enrollment, and staffing — no fee ledger noise."""
    return list_activities(school=school, term=term).exclude(verb__in=FEE_VERBS)


def list_activities_for_teacher(*, school, user, term):
    """Events for the classes this teacher manages and the subjects they teach."""
    from teachers.models import ClassTeacher, TeachingAssignment

    if term is None:
        return Activity.objects.none()

    class_rows = list(
        ClassTeacher.objects.filter(teacher=user, term=term).only(
            'stream_id',
            'class_level_id',
        )
    )
    class_stream_ids = [row.stream_id for row in class_rows if row.stream_id]
    whole_class_level_ids = [row.class_level_id for row in class_rows if not row.stream_id]

    teaching_rows = list(
        TeachingAssignment.objects.filter(teacher=user, term=term).only('id', 'stream_id')
    )
    teaching_ids = [row.id for row in teaching_rows]
    class_stream_set = set(class_stream_ids)
    subject_stream_ids = [
        row.stream_id
        for row in teaching_rows
        if row.stream_id and row.stream_id not in class_stream_set
    ]

    query = Q(pk__in=[])
    if class_stream_ids:
        query |= Q(stream_id__in=class_stream_ids)
    if whole_class_level_ids:
        query |= Q(stream__class_level_id__in=whole_class_level_ids)
    if teaching_ids:
        query |= Q(teaching_assignment_id__in=teaching_ids)
    if subject_stream_ids:
        query |= Q(stream_id__in=subject_stream_ids, verb__in=CLASS_WIDE_VERBS)

    return list_activities(school=school, term=term).filter(query).exclude(verb__in=FEE_VERBS)


def list_activities_for_membership(*, membership, school, term=None):
    """Role-scoped feed for Insights / Activities API."""
    from accounts.models import User

    if membership is None:
        return Activity.objects.none()

    role = membership.role
    if role == User.RoleChoices.ADMIN:
        return list_activities(school=school, term=term)
    if role == User.RoleChoices.ACCOUNTANT:
        return list_activities_for_accountant(school=school, term=term)
    if role == User.RoleChoices.STAFF:
        return list_activities_for_staff(school=school, term=term)
    if role == User.RoleChoices.TEACHER:
        return list_activities_for_teacher(
            school=school,
            user=membership.user,
            term=term,
        )
    return Activity.objects.none()
