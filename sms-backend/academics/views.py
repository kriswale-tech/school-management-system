from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response

from academics.models import ClassLevel, Level
from academics.serializers import AllClassesSerializer
from academics.services.all_classes import get_all_classes
from shared.views import SchoolScopedAPIView
from students.services import resolve_term


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
    tags=['Academics'],
    summary='List active levels',
    description="Returns active levels for the authenticated user's school.",
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
class ActiveLevelListView(SchoolScopedAPIView, ActiveLevelListSerializerMixin):
    def get(self, request):
        levels = Level.objects.filter(
            school=self.school,
            is_active=True,
        ).order_by('order', 'name')
        return Response(self.serialize_levels(levels))


@extend_schema(
    tags=['Academics'],
    summary='List active class levels',
    description="Returns active classes for the authenticated user's school.",
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
class ActiveClassLevelListView(SchoolScopedAPIView):
    def get(self, request):
        class_levels = ClassLevel.objects.filter(
            school=self.school,
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


@extend_schema(
    tags=['Academics'],
    summary='All classes for assignment',
    description=(
        'Returns active levels with flat selectable class entries. '
        'Each entry id is a stream UUID for enrollment. Named streams are listed '
        'as separate entries; classes with only a default stream expose that '
        'default using the class display name. student_count is for the active '
        'term (or optional term query param).'
    ),
    parameters=[
        OpenApiParameter(
            name='term',
            type=str,
            description='Optional term UUID. Defaults to the school active term.',
        ),
    ],
    responses={200: AllClassesSerializer},
)
class AllClassesView(SchoolScopedAPIView):
    def get(self, request):
        term = resolve_term(
            self.school,
            request.query_params.get('term'),
        )
        payload = get_all_classes(school=self.school, term=term)
        return Response(AllClassesSerializer(payload).data)
