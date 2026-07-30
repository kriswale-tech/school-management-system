from drf_spectacular.utils import extend_schema
from rest_framework.response import Response

from schools.services.setup import complete_school_setup
from schools.setup_serializers import SetupStepResponseSerializer
from shared.views import SchoolScopedAPIView

__all__ = ['CompleteSetupView']


@extend_schema(
    summary='Complete school setup',
    description=(
        'Validates that all required setup steps are complete and the school '
        'configuration is ready, then marks setup as finished. The optional '
        'staff step does not block completion.'
    ),
    request=None,
    responses={200: SetupStepResponseSerializer},
)
class CompleteSetupView(SchoolScopedAPIView):
    def post(self, request):
        result = complete_school_setup(self.school)
        return Response(SetupStepResponseSerializer(result).data)
