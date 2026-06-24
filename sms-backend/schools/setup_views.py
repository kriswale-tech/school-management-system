from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.exceptions import cloudinary_error_detail
from schools.models import SchoolSetup
from schools.serializers import SchoolSetupSerializer
from schools.services.setup import advance_setup_step
from schools.setup_serializers import (
    SetupSchoolProfileSerializer,
    SetupStepResponseSerializer,
)


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


@extend_schema(
    summary='Complete school profile setup step',
    description=(
        'Save school profile details including logo. '
        'Advances setup progress and returns the next step.'
    ),
    request=SetupSchoolProfileSerializer,
    responses={200: SetupStepResponseSerializer},
)
class SetupSchoolProfileView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        school = request.user.school
        school_setup, _ = SchoolSetup.objects.get_or_create(school=school)

        serializer = SetupSchoolProfileSerializer(
            school,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        try:
            serializer.save()
        except Exception as exc:
            from cloudinary.exceptions import Error as CloudinaryError

            if isinstance(exc, CloudinaryError):
                raise ValidationError({'logo': cloudinary_error_detail(exc)}) from exc
            raise

        if SchoolSetup.SetupStep.SCHOOL_PROFILE not in (school_setup.completed_steps or []):
            result = advance_setup_step(
                school_setup,
                SchoolSetup.SetupStep.SCHOOL_PROFILE,
            )
        else:
            result = {
                'next_step': school_setup.current_step,
                'completed_steps': school_setup.completed_steps,
                'is_complete': school_setup.current_step == SchoolSetup.SetupStep.COMPLETED,
                'progress_percentage': school_setup.progress_percentage,
            }

        return Response(SetupStepResponseSerializer(result).data)
