from rest_framework.permissions import BasePermission

from accounts.models import User
from accounts.services.capabilities import membership_has_capability
from accounts.services.memberships import NO_ACTIVE_SCHOOL_MESSAGE, get_active_role
from accounts.services.users import can_manage_membership


class HasActiveSchool(BasePermission):
    """Requires a school-scoped token, i.e. the user has selected a school."""

    message = NO_ACTIVE_SCHOOL_MESSAGE

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and getattr(request, 'membership', None) is not None
        )


class HasCapability(BasePermission):
    """Requires a capability resolved from the active membership.

    Set `required_capability` on the view, or subclass and set `capability`.
    """

    message = 'You do not have permission to perform this action.'
    capability = None

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        required = getattr(view, 'required_capability', None) or self.capability
        if not required:
            return False
        return membership_has_capability(
            getattr(request, 'membership', None),
            required,
        )


class HasRole(BasePermission):
    allowed_roles = []

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and get_active_role(request) in self.allowed_roles
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
        return get_active_role(request) in (
            User.RoleChoices.ADMIN,
            User.RoleChoices.STAFF,
        )

    def has_object_permission(self, request, view, obj):
        """obj is the target SchoolMembership within the active school."""
        return can_manage_membership(request.membership, obj)


# Backwards-compatible alias for add-user usage.
CanAddUser = CanManageUser
