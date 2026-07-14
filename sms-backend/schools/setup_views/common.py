from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from schools.models import SchoolSetup
from schools.serializers import SchoolSetupSerializer
from schools.services.setup import advance_setup_if_needed, advance_setup_step

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
class SchoolSetupView(APIView):
    def get(self, request):
        school_setup, _ = SchoolSetup.objects.get_or_create(
            school=request.user.school,
        )
        return Response(SchoolSetupSerializer(school_setup).data)
