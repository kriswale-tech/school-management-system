import logging
from dataclasses import dataclass

from django.db import transaction
from django.db.models import ProtectedError, Q
from rest_framework.exceptions import NotFound, ValidationError

from accounts.models import PhoneOtp, Profile, SchoolMembership, User
from accounts.services.memberships import link_user_to_school

logger = logging.getLogger(__name__)

MANAGEABLE_ROLES_BY_REQUESTER = {
    User.RoleChoices.ADMIN: set(User.RoleChoices.values),
    User.RoleChoices.STAFF: {User.RoleChoices.TEACHER},
}

PROFILE_FIELDS = (
    'profile_picture',
    'bio',
    'date_of_birth',
    'gender',
    'address',
    'phone_number_alt',
)

IDENTITY_FIELDS = ('first_name', 'last_name', 'email')


def manageable_roles(role: str) -> set[str]:
    return MANAGEABLE_ROLES_BY_REQUESTER.get(role, set())


def can_manage_membership(actor: SchoolMembership, target: SchoolMembership) -> bool:
    if actor.school_id != target.school_id:
        return False
    return target.role in manageable_roles(actor.role)


def list_school_memberships(actor: SchoolMembership):
    return (
        SchoolMembership.objects.filter(
            school_id=actor.school_id,
            role__in=manageable_roles(actor.role),
        )
        .select_related('school', 'user', 'user__profile')
        .order_by('user__last_name', 'user__first_name')
    )


def get_school_membership(school, user_id) -> SchoolMembership:
    """Look up a school member by their user id, which is the public identifier."""
    try:
        return SchoolMembership.objects.select_related(
            'school',
            'user',
            'user__profile',
        ).get(user_id=user_id, school=school)
    except SchoolMembership.DoesNotExist as exc:
        raise NotFound('User not found.') from exc


def _ensure_can_manage(actor: SchoolMembership, target: SchoolMembership) -> None:
    if not can_manage_membership(actor, target):
        raise ValidationError({
            'detail': 'You do not have permission to manage this user.',
        })


def _ensure_not_self(actor: SchoolMembership, target: SchoolMembership, *, action: str = 'modify') -> None:
    if actor.user_id == target.user_id:
        raise ValidationError({
            'detail': f'You cannot {action} your own account.',
        })


def _ensure_not_last_admin(target: SchoolMembership) -> None:
    if target.role != User.RoleChoices.ADMIN or not target.is_active:
        return

    active_admin_count = SchoolMembership.objects.filter(
        school_id=target.school_id,
        role=User.RoleChoices.ADMIN,
        is_active=True,
    ).count()
    if active_admin_count <= 1:
        raise ValidationError({
            'detail': 'Cannot remove the last active admin.',
        })


@transaction.atomic
def add_school_member(school, validated_data: dict) -> SchoolMembership:
    """Add someone to a school, reusing their identity when the phone is known."""
    profile_data = {
        field: validated_data[field]
        for field in PROFILE_FIELDS
        if field in validated_data
    }
    phone_number = validated_data['phone_number']
    role = validated_data['role']

    user = User.objects.filter(phone_number=phone_number).first()

    if user is not None:
        # The person already exists elsewhere in the system; their own name and
        # profile stay authoritative, this school just gains access to them.
        membership, _ = link_user_to_school(user, school, role)
        return membership

    user = User.objects.create(
        phone_number=phone_number,
        first_name=validated_data['first_name'],
        last_name=validated_data['last_name'],
        email=validated_data.get('email') or '',
        is_active=True,
    )
    user.set_unusable_password()
    user.save(update_fields=['password'])
    Profile.objects.create(user=user, **profile_data)

    membership, _ = link_user_to_school(user, school, role)
    return membership


def _ensure_can_change_phone_number(actor: SchoolMembership) -> None:
    if actor.role != User.RoleChoices.ADMIN:
        raise ValidationError({
            'phone_number': 'Only admins can change phone numbers.',
        })
    if actor.school.setup_completed:
        raise ValidationError({
            'phone_number': (
                'Phone numbers can only be changed while school setup is incomplete.'
            ),
        })


def _sync_school_contact_phone(school, old_phone: str, new_phone: str) -> None:
    if school.phone_number == old_phone:
        school.phone_number = new_phone
        school.save(update_fields=['phone_number', 'updated_at'])


def _transfer_school_scoped_records(old_user: User, new_user: User, school) -> None:
    """Move teaching records to the corrected identity so nothing is lost."""
    from teachers.models import ClassTeacher, TeachingAssignment

    ClassTeacher.objects.filter(teacher=old_user, term__school=school).update(teacher=new_user)
    TeachingAssignment.objects.filter(teacher=old_user, term__school=school).update(
        teacher=new_user,
    )


def _discard_orphaned_identity(user: User) -> None:
    """Delete an identity left with no school access and no teaching records."""
    from teachers.models import ClassTeacher, TeachingAssignment

    if user.memberships.exists():
        return
    if ClassTeacher.objects.filter(teacher=user).exists():
        return
    if TeachingAssignment.objects.filter(teacher=user).exists():
        return
    if user.last_login is not None:
        return

    PhoneOtp.objects.filter(phone_number=user.phone_number).delete()
    try:
        user.delete()
    except ProtectedError:
        user.is_active = False
        user.save(update_fields=['is_active', 'updated_at'])


def _clone_identity(source: User, phone_number: str, overrides: dict) -> User:
    clone = User.objects.create(
        phone_number=phone_number,
        first_name=overrides.get('first_name', source.first_name),
        last_name=overrides.get('last_name', source.last_name),
        email=overrides.get('email', source.email) or '',
        is_active=source.is_active,
    )
    clone.set_unusable_password()
    clone.save(update_fields=['password'])

    source_profile = Profile.objects.filter(user=source).first()
    profile_data = {}
    if source_profile is not None:
        profile_data = {
            field: getattr(source_profile, field)
            for field in PROFILE_FIELDS
        }
    Profile.objects.create(user=clone, **profile_data)
    return clone


def change_member_phone_number(
    actor: SchoolMembership,
    target: SchoolMembership,
    new_phone: str,
    identity_overrides: dict | None = None,
) -> tuple[SchoolMembership, bool]:
    """Repoint a membership at the correct phone number during school setup.

    An admin editing a phone during setup is correcting a mis-typed number, not
    recording that someone changed SIM, so this acts on the membership rather
    than mutating a phone number other schools may rely on for login.

    Returns the resulting membership and whether an existing person was linked.
    """
    _ensure_can_change_phone_number(actor)

    target_user = target.user
    school = actor.school
    overrides = identity_overrides or {}

    if new_phone == target_user.phone_number:
        return target, False

    existing = User.objects.filter(phone_number=new_phone).first()

    if existing is None:
        shares_identity = target_user.memberships.exclude(pk=target.pk).exists()

        if not shares_identity:
            old_phone = target_user.phone_number
            target_user.phone_number = new_phone
            target_user.save(update_fields=['phone_number', 'updated_at'])
            PhoneOtp.objects.filter(phone_number=old_phone).delete()
            _sync_school_contact_phone(school, old_phone, new_phone)
            return target, False

        # The identity is shared with another school, so split it rather than
        # changing how that person logs in everywhere.
        clone = _clone_identity(target_user, new_phone, overrides)
        _transfer_school_scoped_records(target_user, clone, school)
        target.user = clone
        target.save(update_fields=['user', 'updated_at'])
        logger.info(
            'Split identity %s into %s for school %s',
            target_user.pk,
            clone.pk,
            school.pk,
        )
        return target, False

    # The corrected number belongs to someone already in the system: link them
    # to this school and discard the membership created by mistake.
    membership, _ = link_user_to_school(existing, school, target.role)
    _transfer_school_scoped_records(target_user, existing, school)

    if membership.pk != target.pk:
        target.delete()
        _discard_orphaned_identity(target_user)

    logger.info(
        'Linked existing user %s to school %s in place of %s',
        existing.pk,
        school.pk,
        target_user.pk,
    )
    return membership, True


@dataclass
class UpdateMemberResult:
    membership: SchoolMembership
    linked_existing_user: bool = False


@transaction.atomic
def update_school_member(
    actor: SchoolMembership,
    target: SchoolMembership,
    validated_data: dict,
) -> UpdateMemberResult:
    _ensure_can_manage(actor, target)

    profile_data = {
        field: validated_data.pop(field)
        for field in PROFILE_FIELDS
        if field in validated_data
    }

    if 'role' in validated_data:
        if actor.user_id == target.user_id:
            raise ValidationError({
                'role': 'You cannot change your own role.',
            })

        if (
            target.role == User.RoleChoices.ADMIN
            and validated_data['role'] != User.RoleChoices.ADMIN
        ):
            _ensure_not_last_admin(target)

        if validated_data['role'] not in manageable_roles(actor.role):
            raise ValidationError({
                'role': 'You do not have permission to assign this role.',
            })

        target.role = validated_data['role']
        target.save(update_fields=['role', 'updated_at'])

    linked_existing_user = False
    if 'phone_number' in validated_data:
        target, linked_existing_user = change_member_phone_number(
            actor,
            target,
            validated_data['phone_number'],
            identity_overrides={
                field: validated_data[field]
                for field in IDENTITY_FIELDS
                if field in validated_data
            },
        )

    if not linked_existing_user:
        _update_identity(target.user, validated_data)
        _update_profile(target.user, profile_data)

    return UpdateMemberResult(
        membership=target,
        linked_existing_user=linked_existing_user,
    )


def _update_identity(user: User, validated_data: dict) -> None:
    fields = [field for field in IDENTITY_FIELDS if field in validated_data]
    if not fields:
        return

    for field in fields:
        setattr(user, field, validated_data[field])
    user.save(update_fields=[*fields, 'updated_at'])


def _update_profile(user: User, profile_data: dict) -> None:
    if not profile_data:
        return

    profile, _ = Profile.objects.get_or_create(user=user)
    for field, value in profile_data.items():
        setattr(profile, field, value)
    profile.save(update_fields=[*profile_data, 'updated_at'])


@dataclass
class RemoveMemberResult:
    hard_deleted: bool
    membership: SchoolMembership | None = None


@transaction.atomic
def remove_school_member(
    actor: SchoolMembership,
    target: SchoolMembership,
) -> RemoveMemberResult:
    """Revoke someone's access to this school without touching other schools."""
    _ensure_can_manage(actor, target)
    _ensure_not_self(actor, target, action='delete')
    _ensure_not_last_admin(target)

    target_user = target.user

    if not target.school.setup_completed:
        try:
            target.delete()
        except ProtectedError:
            target.is_active = False
            target.save(update_fields=['is_active', 'updated_at'])
            return RemoveMemberResult(hard_deleted=False, membership=target)

        _discard_orphaned_identity(target_user)
        return RemoveMemberResult(hard_deleted=True)

    target.is_active = False
    target.save(update_fields=['is_active', 'updated_at'])
    return RemoveMemberResult(hard_deleted=False, membership=target)


def email_taken(email: str, *, exclude_user: User | None = None) -> bool:
    queryset = User.objects.filter(Q(email=email), is_active=True)
    if exclude_user is not None:
        queryset = queryset.exclude(pk=exclude_user.pk)
    return queryset.exists()
