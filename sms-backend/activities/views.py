from drf_spectacular.utils import OpenApiParameter, extend_schema

from accounts.capabilities import Capability
from accounts.permissions import HasActiveSchool, HasCapability
from activities.serializers import ActivitySerializer
from activities.services import list_activities_for_membership
from core.pagination import StandardResultsSetPagination, paginated_schema
from schools.models import Term
from shared.views import SchoolScopedAPIView


class ActivityListView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.REPORTS_VIEW
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        tags=['Activities'],
        summary='List recent school activities',
        description=(
            'Newest-first activity feed for the active school, scoped to the '
            'caller\'s role (admin: all; accountant: fees; staff: non-fees; '
            'teacher: assigned classes/subjects). Defaults to the active term.'
        ),
        parameters=[
            OpenApiParameter(
                name='term',
                type=str,
                description='Term UUID. Defaults to the active term.',
            ),
            OpenApiParameter(name='page', type=int),
            OpenApiParameter(name='page_size', type=int),
        ],
        responses={200: paginated_schema(ActivitySerializer, name='PaginatedActivities')},
    )
    def get(self, request):
        term = _resolve_term(self.school, request.query_params.get('term'))
        queryset = list_activities_for_membership(
            membership=request.membership,
            school=self.school,
            term=term,
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(ActivitySerializer(page, many=True).data)


def _resolve_term(school, term_id):
    if term_id:
        term = Term.objects.filter(school=school, id=term_id).first()
        if term is None:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({'term': 'Term not found in this school.'})
        return term
    return Term.objects.filter(school=school, is_active=True).first()
