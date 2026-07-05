from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.exceptions import cloudinary_error_detail
from schools.models import SchoolSetup
from schools.services.setup import advance_setup_step
from schools.setup_serializers import (
    SetupSchoolProfileSerializer,
    SetupStepResponseSerializer,
)
from schools.setup_views.common import advance_setup_if_needed


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
            result = advance_setup_if_needed(
                school_setup,
                SchoolSetup.SetupStep.SCHOOL_PROFILE,
            )

        return Response(SetupStepResponseSerializer(result).data)
