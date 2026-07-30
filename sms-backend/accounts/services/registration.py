import logging
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from rest_framework.exceptions import ValidationError

from academics.services.curriculum import provision_school_curriculum
from accounts.models import SchoolMembership, User
from accounts.services.memberships import link_user_to_school
from schools.models import School, SchoolSetup

logger = logging.getLogger(__name__)

PENDING_SCHOOL_CACHE_PREFIX = 'accounts:pending_school:'
DUPLICATE_SCHOOL_NAME_MESSAGE = (
    'You already administer a school with this name.'
)


def normalize_school_name(name: str) -> str:
    return ' '.join(name.split()).casefold()


def pending_school_cache_key(phone_number: str) -> str:
    return f'{PENDING_SCHOOL_CACHE_PREFIX}{phone_number}'


def stage_pending_school(phone_number: str, school_name: str) -> None:
    """Remember a school the person wants to create until OTP is verified."""
    timeout = (settings.OTP_EXPIRY_MINUTES * 60) + 60
    cache.set(
        pending_school_cache_key(phone_number),
        {'school_name': school_name},
        timeout=timeout,
    )


def get_pending_school(phone_number: str) -> dict | None:
    return cache.get(pending_school_cache_key(phone_number))


def clear_pending_school(phone_number: str) -> None:
    cache.delete(pending_school_cache_key(phone_number))


def find_admin_school_with_name(user: User, school_name: str) -> SchoolMembership | None:
    """Return the user's admin membership for a school with this name, if any."""
    normalized = normalize_school_name(school_name)
    for membership in (
        SchoolMembership.objects.filter(
            user=user,
            role=User.RoleChoices.ADMIN,
            is_active=True,
        )
        .select_related('school')
    ):
        if normalize_school_name(membership.school.name) == normalized:
            return membership
    return None


def ensure_school_name_available(user: User, school_name: str) -> None:
    if find_admin_school_with_name(user, school_name) is not None:
        raise ValidationError({'school_name': DUPLICATE_SCHOOL_NAME_MESSAGE})


def _provision_school(*, name: str, phone_number: str) -> School:
    school = School.objects.create(name=name, phone_number=phone_number)
    SchoolSetup.objects.create(school=school)
    provision_school_curriculum(school)
    return school


@dataclass
class SignUpResult:
    user: User
    linked_existing_account: bool = False


@transaction.atomic
def register_school_admin(validated_data: dict) -> SignUpResult:
    """Start creating a school from signup.

    New phones get an inactive identity and a draft school. Unverified phones
    resume that draft. Verified phones stage the school name for creation after
    OTP, so the create-school form works without bouncing them to login.
    """
    phone_number = validated_data['phone_number']
    school_name = validated_data['school_name']

    active_user = User.objects.filter(
        phone_number=phone_number,
        is_active=True,
    ).first()
    if active_user is not None:
        ensure_school_name_available(active_user, school_name)
        stage_pending_school(phone_number, school_name)
        return SignUpResult(user=active_user, linked_existing_account=True)

    pending_user = User.objects.filter(
        phone_number=phone_number,
        is_active=False,
    ).first()

    if pending_user is not None:
        return SignUpResult(user=_resume_pending_signup(pending_user, validated_data))

    school = _provision_school(
        name=school_name,
        phone_number=phone_number,
    )

    user = User.objects.create(
        phone_number=phone_number,
        email=validated_data['email'],
        first_name=validated_data['first_name'],
        last_name=validated_data['last_name'],
        is_active=False,
    )
    link_user_to_school(user, school, User.RoleChoices.ADMIN)
    return SignUpResult(user=user)


def _resume_pending_signup(user: User, validated_data: dict) -> User:
    """Reuse the unverified account and its half-built school."""
    membership = (
        SchoolMembership.objects.filter(user=user)
        .select_related('school')
        .first()
    )

    if membership is None:
        school = _provision_school(
            name=validated_data['school_name'],
            phone_number=validated_data['phone_number'],
        )
        link_user_to_school(user, school, User.RoleChoices.ADMIN)
    else:
        school = membership.school
        school.name = validated_data['school_name']
        school.phone_number = validated_data['phone_number']
        school.save(update_fields=['name', 'phone_number', 'updated_at'])

        SchoolSetup.objects.get_or_create(school=school)

        if membership.role != User.RoleChoices.ADMIN or not membership.is_active:
            membership.role = User.RoleChoices.ADMIN
            membership.is_active = True
            membership.save(update_fields=['role', 'is_active', 'updated_at'])

    user.email = validated_data['email']
    user.first_name = validated_data['first_name']
    user.last_name = validated_data['last_name']
    user.save(update_fields=['email', 'first_name', 'last_name', 'updated_at'])
    return user


@dataclass
class CompleteSignupResult:
    user: User
    membership: SchoolMembership | None = None
    linked_existing_account: bool = False


@transaction.atomic
def complete_pending_school_creation(user: User) -> SchoolMembership | None:
    """Create the school staged at signup for a returning verified user."""
    pending = get_pending_school(user.phone_number)
    if pending is None:
        return None

    school_name = pending['school_name']
    ensure_school_name_available(user, school_name)

    school = _provision_school(
        name=school_name,
        phone_number=user.phone_number,
    )
    membership, _ = link_user_to_school(user, school, User.RoleChoices.ADMIN)
    clear_pending_school(user.phone_number)
    logger.info(
        'Created additional school %s for returning user %s via signup',
        school.pk,
        user.pk,
    )
    return membership


@transaction.atomic
def create_additional_school(user: User, validated_data: dict) -> SchoolMembership:
    """Let an already-verified person start another school they will administer."""
    school_name = validated_data['school_name']
    ensure_school_name_available(user, school_name)

    school = _provision_school(
        name=school_name,
        phone_number=validated_data.get('phone_number') or user.phone_number,
    )
    membership, _ = link_user_to_school(user, school, User.RoleChoices.ADMIN)
    logger.info('User %s created additional school %s', user.pk, school.pk)
    return membership
