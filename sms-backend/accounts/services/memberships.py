import logging

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from rest_framework.exceptions import NotAuthenticated, PermissionDenied, ValidationError

from accounts.models import SchoolMembership, User

logger = logging.getLogger(__name__)

from schools.models import School

NO_SCHOOL_ACCESS_MESSAGE = 'You do not have access to any school.'
NO_ACTIVE_SCHOOL_MESSAGE = 'Select a school before using this endpoint.'
SCHOOL_UNAVAILABLE_MESSAGE = (
    'This school is suspended or archived and cannot be used right now.'
)

ACCESSIBLE_SCHOOL_STATUSES = (School.Status.PENDING, School.Status.ACTIVE)


def active_memberships(user: User) -> QuerySet[SchoolMembership]:
    return (
        SchoolMembership.objects.filter(
            user=user,
            is_active=True,
            school__status__in=ACCESSIBLE_SCHOOL_STATUSES,
        )
        .select_related('school')
    )


def get_active_membership(user: User, school_id) -> SchoolMembership | None:
    membership = (
        SchoolMembership.objects.filter(
            user=user,
            school_id=school_id,
            is_active=True,
        )
        .select_related('school')
        .first()
    )
    if membership is None:
        return None
    if membership.school.status not in ACCESSIBLE_SCHOOL_STATUSES:
        return None
    return membership


def resolve_membership(user: User, school_id) -> SchoolMembership:
    """Resolve a token's school claim, rejecting revoked access."""
    membership = (
        SchoolMembership.objects.filter(
            user=user,
            school_id=school_id,
            is_active=True,
        )
        .select_related('school')
        .first()
    )
    if membership is None:
        raise PermissionDenied('Your access to this school is no longer active.')
    if membership.school.status not in ACCESSIBLE_SCHOOL_STATUSES:
        raise PermissionDenied(SCHOOL_UNAVAILABLE_MESSAGE)
    return membership


def preferred_membership(user: User) -> SchoolMembership | None:
    """The membership to pre-select in the school picker (most recently used)."""
    return active_memberships(user).first()


def sole_membership(user: User) -> SchoolMembership | None:
    """The only active membership, or None when the user must choose."""
    memberships = list(active_memberships(user)[:2])
    if len(memberships) == 1:
        return memberships[0]
    return None


def touch_membership(membership: SchoolMembership) -> None:
    membership.last_active_at = timezone.now()
    membership.save(update_fields=['last_active_at', 'updated_at'])


@transaction.atomic
def link_user_to_school(
    user: User,
    school,
    role: str,
    *,
    reactivate: bool = True,
) -> tuple[SchoolMembership, bool]:
    """Give an existing identity access to a school. Returns (membership, created)."""
    existing = SchoolMembership.objects.filter(user=user, school=school).first()
    if existing is not None and existing.is_active:
        raise ValidationError({
            'phone_number': 'This person is already a member of this school.',
        })

    will_consume_seat = existing is None or (not existing.is_active and reactivate)
    if will_consume_seat:
        from billing.services.capacity import ensure_can_add_staff

        ensure_can_add_staff(school, additional=1)

    if existing is None:
        membership = SchoolMembership.objects.create(
            user=user,
            school=school,
            role=role,
        )
        logger.info(
            'Linked user %s to school %s as %s',
            user.pk,
            school.pk,
            role,
        )
        return membership, True

    if not reactivate:
        raise ValidationError({
            'phone_number': 'This person previously belonged to this school.',
        })

    existing.is_active = True
    existing.role = role
    existing.save(update_fields=['is_active', 'role', 'updated_at'])
    return existing, False


def deactivate_membership(membership: SchoolMembership) -> None:
    if not membership.is_active:
        return
    membership.is_active = False
    membership.save(update_fields=['is_active', 'updated_at'])


def has_active_membership(user: User, school_id, *, role: str | None = None) -> bool:
    queryset = SchoolMembership.objects.filter(
        user=user,
        school_id=school_id,
        is_active=True,
    )
    if role is not None:
        queryset = queryset.filter(role=role)
    return queryset.exists()


def get_active_membership_for_request(request) -> SchoolMembership:
    """The membership the current request is scoped to.

    Raises when the caller holds an identity-only token, which is what keeps a
    multi-school user from reaching school data before choosing a school.
    """
    if not request.user.is_authenticated:
        raise NotAuthenticated()

    membership = getattr(request, 'membership', None)
    if membership is not None:
        return membership

    if getattr(request, 'membership_revoked', False):
        raise PermissionDenied('Your access to this school is no longer active.')

    raise PermissionDenied(NO_ACTIVE_SCHOOL_MESSAGE)


def get_active_school(request):
    return get_active_membership_for_request(request).school


def get_active_role(request) -> str | None:
    membership = getattr(request, 'membership', None)
    return membership.role if membership else None
