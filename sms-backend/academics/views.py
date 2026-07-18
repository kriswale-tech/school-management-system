from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from academics.models import ClassLevel, Level


class ActiveLevelListSerializerMixin:
    @staticmethod
    def serialize_levels(levels):
        return [
            {
                'id': level.id,
                'name': level.name,
                'order': level.order,
            }
            for level in levels
        ]


@extend_schema(
    summary='List active levels',
    description='Returns active levels for the authenticated user\'s school.',
    responses={
        200: {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'string', 'format': 'uuid'},
                    'name': {'type': 'string'},
                    'order': {'type': 'integer'},
                },
            },
        },
    },
)
class ActiveLevelListView(APIView, ActiveLevelListSerializerMixin):
    def get(self, request):
        levels = Level.objects.filter(
            school=request.user.school,
            is_active=True,
        ).order_by('order', 'name')
        return Response(self.serialize_levels(levels))


@extend_schema(
    summary='List active class levels',
    description='Returns active classes for the authenticated user\'s school.',
    responses={
        200: {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'string', 'format': 'uuid'},
                    'name': {'type': 'string'},
                    'level_id': {'type': 'string', 'format': 'uuid'},
                    'level_name': {'type': 'string'},
                    'order': {'type': 'integer'},
                },
            },
        },
    },
)
class ActiveClassLevelListView(APIView):
    def get(self, request):
        class_levels = ClassLevel.objects.filter(
            school=request.user.school,
            is_active=True,
            level__is_active=True,
        ).select_related('level').order_by('level__order', 'order', 'name')

        return Response([
            {
                'id': class_level.id,
                'name': class_level.name,
                'level_id': class_level.level_id,
                'level_name': class_level.level.name,
                'order': class_level.order,
            }
            for class_level in class_levels
        ])
