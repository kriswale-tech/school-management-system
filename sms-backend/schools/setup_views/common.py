from drf_spectacular.utils import extend_schema
from rest_framework.response import Response

from schools.models import SchoolSetup
from schools.serializers import SchoolSetupSerializer
from schools.services.setup import advance_setup_if_needed, advance_setup_step
from shared.views import SchoolScopedAPIView

__all__ = [
    'SchoolSetupView',
    'advance_setup_if_needed',
    'advance_setup_step',
]


@extend_schema(
    summary='Get school setup',
    description='Get the setup for the school',
    responses={200: SchoolSetupSerializer},
)
class SchoolSetupView(SchoolScopedAPIView):
    def get(self, request):
        school_setup, _ = SchoolSetup.objects.get_or_create(
            school=self.school,
        )
        return Response(SchoolSetupSerializer(school_setup).data)
