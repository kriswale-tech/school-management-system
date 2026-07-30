from drf_spectacular.utils import extend_schema
from rest_framework.response import Response

from shared.views import SchoolScopedAPIView
from .serializers import SchoolSerializer


@extend_schema(
    summary="Get school",
    description="Get the school the session is currently scoped to.",
    responses={
        200: SchoolSerializer,
    }
)
class SchoolView(SchoolScopedAPIView):
    def get(self, request):
        return Response(SchoolSerializer(self.school).data)

    # update school.
