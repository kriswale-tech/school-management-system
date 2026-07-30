from drf_spectacular.utils import extend_schema
from rest_framework.response import Response

from schools.models import SchoolSetup
from schools.services.academic import get_academic_year_setup
from schools.services.setup import require_prior_setup_steps
from schools.setup_serializers import (
    AcademicYearTermDataSerializer,
    SetupAcademicYearTermPostResponseSerializer,
    SetupAcademicYearTermSerializer,
)
from schools.setup_views.common import advance_setup_if_needed
from shared.views import SchoolScopedAPIView


@extend_schema(
    methods=['GET'],
    summary='Get academic year and term setup',
    description='Returns the active academic year, term schedule, and current term.',
    responses={200: AcademicYearTermDataSerializer},
)
@extend_schema(
    methods=['POST'],
    summary='Save academic year and term setup',
    description=(
        'Creates or updates the active academic year and three-term schedule. '
        'Academic year dates are derived from the first and third term dates.'
    ),
    request=SetupAcademicYearTermSerializer,
    responses={200: SetupAcademicYearTermPostResponseSerializer},
)
class SetupAcademicYearTermView(SchoolScopedAPIView):
    def get(self, request):
        data = get_academic_year_setup(self.school)
        return Response(AcademicYearTermDataSerializer(data).data)

    def post(self, request):
        school = self.school
        school_setup, _ = SchoolSetup.objects.get_or_create(school=school)

        require_prior_setup_steps(
            school_setup,
            SchoolSetup.SetupStep.ACADEMIC_YEAR_TERM,
        )

        serializer = SetupAcademicYearTermSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        academic_data = serializer.save(school)

        setup_result = advance_setup_if_needed(
            school_setup,
            SchoolSetup.SetupStep.ACADEMIC_YEAR_TERM,
        )

        return Response(
            SetupAcademicYearTermPostResponseSerializer({
                **academic_data,
                **setup_result,
            }).data,
        )

