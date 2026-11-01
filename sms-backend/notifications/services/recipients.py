"""Resolve SchoolMembership recipients for notification fan-out."""

from django.db.models import Q, QuerySet

from accounts.models import SchoolMembership, User


def active_memberships(
    school,
    *,
    roles: set[str] | list[str] | tuple[str, ...] | None = None,
    user_ids=None,
) -> QuerySet[SchoolMembership]:
    queryset = SchoolMembership.objects.filter(school=school, is_active=True)
    if roles is not None:
        queryset = queryset.filter(role__in=roles)
    if user_ids is not None:
        queryset = queryset.filter(user_id__in=list(user_ids))
    return queryset.select_related('user')


def admins_of(school) -> QuerySet[SchoolMembership]:
    return active_memberships(school, roles={User.RoleChoices.ADMIN})


def staff_of(school) -> QuerySet[SchoolMembership]:
    return active_memberships(school, roles={User.RoleChoices.STAFF})


def admins_and_staff(school) -> QuerySet[SchoolMembership]:
    return active_memberships(
        school,
        roles={User.RoleChoices.ADMIN, User.RoleChoices.STAFF},
    )


def accountants_of(school) -> QuerySet[SchoolMembership]:
    return active_memberships(school, roles={User.RoleChoices.ACCOUNTANT})


def all_active_members(school) -> QuerySet[SchoolMembership]:
    return active_memberships(school)


def membership_for_user(school, user_id) -> SchoolMembership | None:
    if user_id is None:
        return None
    return (
        SchoolMembership.objects.filter(
            school=school,
            user_id=user_id,
            is_active=True,
        )
        .select_related('user')
        .first()
    )


def class_teacher_memberships(*, school, term, stream) -> QuerySet[SchoolMembership]:
    """Teachers assigned as class teacher for this stream (or whole-level)."""
    from teachers.models import ClassTeacher

    if term is None or stream is None:
        return SchoolMembership.objects.none()

    teacher_ids = ClassTeacher.objects.filter(
        Q(stream_id=stream.id)
        | Q(class_level_id=stream.class_level_id, stream__isnull=True),
        term=term,
    ).values_list('teacher_id', flat=True)
    return active_memberships(
        school,
        roles={User.RoleChoices.TEACHER},
        user_ids=teacher_ids,
    )


def teacher_memberships_for_users(school, user_ids) -> QuerySet[SchoolMembership]:
    return active_memberships(
        school,
        roles={User.RoleChoices.TEACHER},
        user_ids=user_ids,
    )


def exclude_user(queryset: QuerySet[SchoolMembership], user) -> QuerySet[SchoolMembership]:
    if user is None:
        return queryset
    return queryset.exclude(user_id=getattr(user, 'id', user))
