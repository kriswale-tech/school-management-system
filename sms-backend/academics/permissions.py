from rest_framework.permissions import BasePermission


class CanMutateCurriculumRecord(BasePermission):
    """Allow mutation only on school-defined (non-system-generated) curriculum rows."""

    message = 'System-generated curriculum records cannot be modified.'

    def has_object_permission(self, request, view, obj):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return not getattr(obj, 'is_system_generated', False)
