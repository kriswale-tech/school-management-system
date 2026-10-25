from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response

from accounts.capabilities import Capability
from accounts.permissions import HasActiveSchool, HasCapability
from reports.serializers import (
    ByClassSerializer,
    BySubjectSerializer,
    EnrollmentSerializer,
    FeesAcademicRiskSerializer,
    FilterOptionsSerializer,
    FinanceSerializer,
    GradeDistributionSerializer,
    OverviewSerializer,
    StaffCapacitySerializer,
    StudentTrendsSerializer,
    SubjectHeatmapSerializer,
    TeacherDeskSerializer,
    WorkflowSerializer,
)
from reports.services import (
    get_by_class,
    get_by_subject,
    get_enrollment,
    get_fees_academic_risk,
    get_filter_options,
    get_finance,
    get_grade_distribution,
    get_overview,
    get_staff_capacity,
    get_student_trends,
    get_subject_heatmap,
    get_teacher_desk,
    get_workflow,
)
from shared.views import SchoolScopedAPIView


def _query_filters(request):
    return {
        'term_id': request.query_params.get('term_id') or None,
        'level_id': request.query_params.get('level_id') or None,
        'class_level_id': request.query_params.get('class_level_id') or None,
    }


COMMON_PARAMS = [
    OpenApiParameter(name='term_id', required=False, type=str),
    OpenApiParameter(name='level_id', required=False, type=str),
    OpenApiParameter(name='class_level_id', required=False, type=str),
]


class ReportsFilterOptionsView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.REPORTS_VIEW

    @extend_schema(
        tags=['Reports'],
        summary='Reports filter options',
        responses={200: FilterOptionsSerializer},
    )
    def get(self, request):
        payload = get_filter_options(school=self.school, membership=self.membership)
        return Response(FilterOptionsSerializer(payload).data)


class ReportsOverviewView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.REPORTS_VIEW

    @extend_schema(
        tags=['Reports'],
        summary='Reports overview KPIs',
        parameters=[
            *COMMON_PARAMS,
            OpenApiParameter(name='compare_term_id', required=False, type=str),
        ],
        responses={200: OverviewSerializer},
    )
    def get(self, request):
        filters = _query_filters(request)
        payload = get_overview(
            school=self.school,
            membership=self.membership,
            compare_term_id=request.query_params.get('compare_term_id') or None,
            **filters,
        )
        return Response(OverviewSerializer(payload).data)


class ReportsByClassView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.REPORTS_VIEW

    @extend_schema(
        tags=['Reports'],
        summary='Average performance by class',
        parameters=COMMON_PARAMS,
        responses={200: ByClassSerializer},
    )
    def get(self, request):
        payload = get_by_class(
            school=self.school,
            membership=self.membership,
            **_query_filters(request),
        )
        return Response(ByClassSerializer(payload).data)


class ReportsBySubjectView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.REPORTS_VIEW

    @extend_schema(
        tags=['Reports'],
        summary='Average performance by subject',
        parameters=COMMON_PARAMS,
        responses={200: BySubjectSerializer},
    )
    def get(self, request):
        payload = get_by_subject(
            school=self.school,
            membership=self.membership,
            **_query_filters(request),
        )
        return Response(BySubjectSerializer(payload).data)


class ReportsGradeDistributionView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.REPORTS_VIEW

    @extend_schema(
        tags=['Reports'],
        summary='Score / grade distribution for one class',
        description=(
            'Requires class_level_id. Grade and grade+position classes return '
            'letter/number bands; position-only classes return score ranges '
            '(mode=score_bands) for the same pie chart.'
        ),
        parameters=COMMON_PARAMS,
        responses={200: GradeDistributionSerializer},
    )
    def get(self, request):
        payload = get_grade_distribution(
            school=self.school,
            membership=self.membership,
            **_query_filters(request),
        )
        return Response(GradeDistributionSerializer(payload).data)


class ReportsStudentTrendsView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.REPORTS_VIEW

    @extend_schema(
        tags=['Reports'],
        summary='Top and at-risk student trends',
        parameters=[
            *COMMON_PARAMS,
            OpenApiParameter(name='limit', required=False, type=int),
        ],
        responses={200: StudentTrendsSerializer},
    )
    def get(self, request):
        payload = get_student_trends(
            school=self.school,
            membership=self.membership,
            limit=request.query_params.get('limit') or 20,
            **_query_filters(request),
        )
        return Response(StudentTrendsSerializer(payload).data)


class ReportsSubjectHeatmapView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.REPORTS_VIEW

    @extend_schema(
        tags=['Reports'],
        summary='Subject performance heat map',
        parameters=COMMON_PARAMS,
        responses={200: SubjectHeatmapSerializer},
    )
    def get(self, request):
        payload = get_subject_heatmap(
            school=self.school,
            membership=self.membership,
            **_query_filters(request),
        )
        return Response(SubjectHeatmapSerializer(payload).data)


class ReportsWorkflowView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.REPORTS_VIEW

    @extend_schema(
        tags=['Reports'],
        summary='Assessment workflow progress',
        parameters=[
            OpenApiParameter(name='term_id', required=False, type=str),
            OpenApiParameter(name='level_id', required=False, type=str),
        ],
        responses={200: WorkflowSerializer},
    )
    def get(self, request):
        payload = get_workflow(
            school=self.school,
            membership=self.membership,
            term_id=request.query_params.get('term_id') or None,
            level_id=request.query_params.get('level_id') or None,
        )
        return Response(WorkflowSerializer(payload).data)


class ReportsFeesAcademicRiskView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.REPORTS_VIEW

    @extend_schema(
        tags=['Reports'],
        summary='Fee debtors with academic risk',
        parameters=[
            OpenApiParameter(name='term_id', required=False, type=str),
            OpenApiParameter(name='limit', required=False, type=int),
        ],
        responses={200: FeesAcademicRiskSerializer},
    )
    def get(self, request):
        payload = get_fees_academic_risk(
            school=self.school,
            membership=self.membership,
            term_id=request.query_params.get('term_id') or None,
            limit=request.query_params.get('limit') or 10,
        )
        return Response(FeesAcademicRiskSerializer(payload).data)


class ReportsFinanceView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.REPORTS_VIEW

    @extend_schema(
        tags=['Reports'],
        summary='Finance insights',
        parameters=[
            OpenApiParameter(name='term_id', required=False, type=str),
            OpenApiParameter(name='limit', required=False, type=int),
        ],
        responses={200: FinanceSerializer},
    )
    def get(self, request):
        payload = get_finance(
            school=self.school,
            membership=self.membership,
            term_id=request.query_params.get('term_id') or None,
            limit=request.query_params.get('limit') or 10,
        )
        return Response(FinanceSerializer(payload).data)


class ReportsEnrollmentView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.REPORTS_VIEW

    @extend_schema(
        tags=['Reports'],
        summary='Enrollment and retention insights',
        parameters=[OpenApiParameter(name='term_id', required=False, type=str)],
        responses={200: EnrollmentSerializer},
    )
    def get(self, request):
        payload = get_enrollment(
            school=self.school,
            membership=self.membership,
            term_id=request.query_params.get('term_id') or None,
        )
        return Response(EnrollmentSerializer(payload).data)


class ReportsStaffCapacityView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.REPORTS_VIEW

    @extend_schema(
        tags=['Reports'],
        summary='Teacher load insights',
        parameters=[OpenApiParameter(name='term_id', required=False, type=str)],
        responses={200: StaffCapacitySerializer},
    )
    def get(self, request):
        payload = get_staff_capacity(
            school=self.school,
            membership=self.membership,
            term_id=request.query_params.get('term_id') or None,
        )
        return Response(StaffCapacitySerializer(payload).data)


class ReportsTeacherDeskView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.REPORTS_VIEW

    @extend_schema(
        tags=['Reports'],
        summary='Teacher class and subject performance desk',
        parameters=[OpenApiParameter(name='term_id', required=False, type=str)],
        responses={200: TeacherDeskSerializer},
    )
    def get(self, request):
        payload = get_teacher_desk(
            school=self.school,
            membership=self.membership,
            term_id=request.query_params.get('term_id') or None,
        )
        return Response(TeacherDeskSerializer(payload).data)
