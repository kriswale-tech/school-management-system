from drf_spectacular.utils import extend_schema
from rest_framework.response import Response

from schools.services.assessment import (
    complete_assessment_setup,
    get_assessment_setup,
    save_level_assessment_config,
)
from schools.setup_serializers.assessment import (
    SaveLevelAssessmentConfigSerializer,
    SetupAssessmentDataSerializer,
    SetupAssessmentLevelSerializer,
)
from schools.setup_serializers.common import SetupStepResponseSerializer
from shared.views import SchoolScopedAPIView


@extend_schema(
    summary='Get assessment setup',
    description=(
        'Returns grade templates and assessment config for every active level '
        'in the school. Levels without a config yet have config set to null. '
        'Inactive levels are omitted; existing configs for inactive levels are kept.'
    ),
    responses={200: SetupAssessmentDataSerializer},
)
class SetupAssessmentView(SchoolScopedAPIView):
    def get(self, request):
        data = get_assessment_setup(self.school)
        return Response(SetupAssessmentDataSerializer(data).data)


@extend_schema(
    summary='Save assessment config for a level',
    description=(
        'Creates or updates assessment configuration for an active level. '
        'Weights must sum to 100. When result type includes grades, grade_type '
        'and contiguous 0–100 grade bands are required. When result type is '
        'position only, grade_type and grade_bands are ignored if sent.'
    ),
    request=SaveLevelAssessmentConfigSerializer,
    responses={200: SetupAssessmentLevelSerializer},
)
class SetupAssessmentLevelConfigView(SchoolScopedAPIView):
    def put(self, request, level_id):
        serializer = SaveLevelAssessmentConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = save_level_assessment_config(
            self.school,
            level_id=level_id,
            **serializer.validated_data,
        )
        return Response(SetupAssessmentLevelSerializer(data).data)


@extend_schema(
    summary='Complete assessment setup',
    description=(
        'Validates that every active level has a complete assessment config, '
        'then advances setup to the next step.'
    ),
    request=None,
    responses={200: SetupStepResponseSerializer},
)
class CompleteAssessmentSetupView(SchoolScopedAPIView):
    def post(self, request):
        result = complete_assessment_setup(self.school)
        return Response(SetupStepResponseSerializer(result).data)
