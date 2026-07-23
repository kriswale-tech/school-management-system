from dataclasses import dataclass

from django.db import transaction
from django.db.models import ProtectedError
from rest_framework.exceptions import NotFound, ValidationError

from accounts.models import PhoneOtp, Profile, User

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


def can_manage_user(actor: User, target: User) -> bool:
    if actor.school_id != target.school_id:
        return False
    manageable_roles = MANAGEABLE_ROLES_BY_REQUESTER.get(actor.role, set())
    return target.role in manageable_roles


def list_school_users(actor: User):
    manageable_roles = MANAGEABLE_ROLES_BY_REQUESTER.get(actor.role, set())
    return (
        User.objects.filter(school=actor.school, role__in=manageable_roles)
        .select_related('school', 'profile')
        .order_by('last_name', 'first_name')
    )


def get_school_user(school, user_id) -> User:
    try:
        return User.objects.select_related('school', 'profile').get(
            pk=user_id,
            school=school,
        )
    except User.DoesNotExist as exc:
        raise NotFound('User not found.') from exc


def _ensure_can_manage(actor: User, target: User) -> None:
    if not can_manage_user(actor, target):
        raise ValidationError({
            'detail': 'You do not have permission to manage this user.',
        })


def _ensure_not_self(actor: User, target: User, *, action: str = 'modify') -> None:
    if actor.pk == target.pk:
        raise ValidationError({
            'detail': f'You cannot {action} your own account.',
        })


def _ensure_not_last_admin(target: User) -> None:
    if target.role != User.RoleChoices.ADMIN or not target.is_active:
        return

    active_admin_count = User.objects.filter(
        school=target.school,
        role=User.RoleChoices.ADMIN,
        is_active=True,
    ).count()
    if active_admin_count <= 1:
        raise ValidationError({
            'detail': 'Cannot remove the last active admin.',
        })


def _ensure_can_change_phone_number(actor: User, target: User) -> None:
    if actor.role != User.RoleChoices.ADMIN:
        raise ValidationError({
            'phone_number': 'Only admins can change phone numbers.',
        })
    if target.school.setup_completed:
        raise ValidationError({
            'phone_number': (
                'Phone numbers can only be changed while school setup is incomplete.'
            ),
        })


@transaction.atomic
def update_user(actor: User, target: User, validated_data: dict) -> User:
    _ensure_can_manage(actor, target)

    profile_data = {
        field: validated_data.pop(field)
        for field in PROFILE_FIELDS
        if field in validated_data
    }

    if 'role' in validated_data:
        if actor.pk == target.pk:
            raise ValidationError({
                'role': 'You cannot change your own role.',
            })

        if (
            target.role == User.RoleChoices.ADMIN
            and validated_data['role'] != User.RoleChoices.ADMIN
        ):
            _ensure_not_last_admin(target)

        allowed_roles = MANAGEABLE_ROLES_BY_REQUESTER.get(actor.role, set())
        if validated_data['role'] not in allowed_roles:
            raise ValidationError({
                'role': 'You do not have permission to assign this role.',
            })

    user_fields = []
    for field in ('first_name', 'last_name', 'email', 'role'):
        if field in validated_data:
            setattr(target, field, validated_data[field])
            user_fields.append(field)

    if 'phone_number' in validated_data:
        new_phone = validated_data['phone_number']
        if new_phone != target.phone_number:
            _ensure_can_change_phone_number(actor, target)
            old_phone = target.phone_number
            target.phone_number = new_phone
            user_fields.append('phone_number')
            PhoneOtp.objects.filter(phone_number=old_phone).delete()

            if target.school.phone_number == old_phone:
                target.school.phone_number = new_phone
                target.school.save(update_fields=['phone_number', 'updated_at'])

    if user_fields:
        target.save(update_fields=[*user_fields, 'updated_at'])

    if profile_data:
        profile, _ = Profile.objects.get_or_create(user=target)
        profile_fields = []
        for field, value in profile_data.items():
            setattr(profile, field, value)
            profile_fields.append(field)
        profile.save(update_fields=[*profile_fields, 'updated_at'])

    return target


@dataclass
class DeleteUserResult:
    hard_deleted: bool
    user: User | None = None


@transaction.atomic
def delete_user(actor: User, target: User) -> DeleteUserResult:
    _ensure_can_manage(actor, target)
    _ensure_not_self(actor, target, action='delete')
    _ensure_not_last_admin(target)

    if not target.school.setup_completed:
        try:
            target.delete()
            return DeleteUserResult(hard_deleted=True)
        except ProtectedError:
            target.is_active = False
            target.save(update_fields=['is_active', 'updated_at'])
            return DeleteUserResult(hard_deleted=False, user=target)

    target.is_active = False
    target.save(update_fields=['is_active', 'updated_at'])
    return DeleteUserResult(hard_deleted=False, user=target)
