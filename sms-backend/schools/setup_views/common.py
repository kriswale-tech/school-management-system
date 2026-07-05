from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from schools.models import SchoolSetup
from schools.serializers import SchoolSetupSerializer
from schools.services.setup import advance_setup_step


def advance_setup_if_needed(school_setup, step):
    if step not in (school_setup.completed_steps or []):
        return advance_setup_step(school_setup, step)

    return {
        'next_step': school_setup.current_step,
        'completed_steps': school_setup.completed_steps,
        'is_complete': school_setup.current_step == SchoolSetup.SetupStep.COMPLETED,
        'progress_percentage': school_setup.progress_percentage,
    }


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
