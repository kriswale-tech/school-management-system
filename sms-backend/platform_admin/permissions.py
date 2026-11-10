from rest_framework.permissions import BasePermission

from platform_admin.models import PlatformUser


class IsPlatformAuthenticated(BasePermission):
    message = 'Platform authentication required.'

    def has_permission(self, request, view):
        user = getattr(request, 'platform_user', None)
        if user is None and isinstance(request.user, PlatformUser):
            user = request.user
        return isinstance(user, PlatformUser) and user.is_active


class HasPlatformRole(BasePermission):
    """Require one of `allowed_roles` set on the view."""

    message = 'You do not have permission to perform this action.'

    def has_permission(self, request, view):
        user = getattr(request, 'platform_user', None)
        if not isinstance(user, PlatformUser) or not user.is_active:
            return False
        allowed = getattr(view, 'allowed_roles', None) or []
        return user.role in allowed
