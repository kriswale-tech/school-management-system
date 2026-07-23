from rest_framework.permissions import BasePermission

from accounts.models import User
from accounts.services.users import can_manage_user


class HasRole(BasePermission):
    allowed_roles = []

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in self.allowed_roles
        )


class IsAdmin(HasRole):
    allowed_roles = [User.RoleChoices.ADMIN]


class IsStaff(HasRole):
    allowed_roles = [User.RoleChoices.STAFF]


class IsAccountant(HasRole):
    allowed_roles = [User.RoleChoices.ACCOUNTANT]


class IsTeacher(HasRole):
    allowed_roles = [User.RoleChoices.TEACHER]


class CanManageUser(BasePermission):
    message = 'You do not have permission to manage users.'

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.role in (
            User.RoleChoices.ADMIN,
            User.RoleChoices.STAFF,
        )

    def has_object_permission(self, request, view, obj):
        return can_manage_user(request.user, obj)


# Backwards-compatible alias for add-user usage.
CanAddUser = CanManageUser
