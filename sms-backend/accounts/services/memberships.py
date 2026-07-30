import logging

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from rest_framework.exceptions import NotAuthenticated, PermissionDenied, ValidationError

from accounts.models import SchoolMembership, User

logger = logging.getLogger(__name__)

NO_SCHOOL_ACCESS_MESSAGE = 'You do not have access to any school.'
NO_ACTIVE_SCHOOL_MESSAGE = 'Select a school before using this endpoint.'


def active_memberships(user: User) -> QuerySet[SchoolMembership]:
    return (
        SchoolMembership.objects.filter(user=user, is_active=True)
        .select_related('school')
    )


def get_active_membership(user: User, school_id) -> SchoolMembership | None:
    return (
        SchoolMembership.objects.filter(
            user=user,
            school_id=school_id,
            is_active=True,
        )
        .select_related('school')
        .first()
    )


def resolve_membership(user: User, school_id) -> SchoolMembership:
    """Resolve a token's school claim, rejecting revoked access."""
    membership = get_active_membership(user, school_id)
    if membership is None:
        raise PermissionDenied('Your access to this school is no longer active.')
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
    membership, created = SchoolMembership.objects.get_or_create(
        user=user,
        school=school,
        defaults={'role': role},
    )

    if created:
        logger.info(
            'Linked user %s to school %s as %s',
            user.pk,
            school.pk,
            role,
        )
        return membership, True

    if membership.is_active:
        raise ValidationError({
            'phone_number': 'This person is already a member of this school.',
        })

    if not reactivate:
        raise ValidationError({
            'phone_number': 'This person previously belonged to this school.',
        })

    membership.is_active = True
    membership.role = role
    membership.save(update_fields=['is_active', 'role', 'updated_at'])
    return membership, False


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
