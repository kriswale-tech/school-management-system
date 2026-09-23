from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from accounts.capabilities import Capability
from accounts.permissions import HasActiveSchool, HasCapability
from assessments.serializers import (
    AdminAssessmentDetailSerializer,
    AdminAssessmentFilterOptionsSerializer,
    AdminAssessmentOverviewSerializer,
    ApproveClassStudentsSerializer,
    AssessmentWorkspaceSerializer,
    CaItemSerializer,
    CaItemWriteSerializer,
    ClassTeacherAssessmentDetailSerializer,
    ClassTeacherAssessmentOverviewSerializer,
    CorrectionActionResponseSerializer,
    CorrectionActionSerializer,
    CorrectionReviewSerializer,
    PublishStudentsSerializer,
    SaveMarksSerializer,
    StoredStudentReportSerializer,
    StudentReportPreviewSerializer,
)
from assessments.services.admin_overview import (
    get_admin_assessment_detail,
    get_admin_assessment_filter_options,
    list_admin_assessment_overview,
    release_admin_students,
)
from assessments.services.corrections import (
    reject_class_teacher_student,
    reject_or_reopen_student,
    request_reopen_student,
    review_reopen_request,
)
from assessments.services.report import get_student_report_preview
from assessments.services.report_pdf import generate_student_report, get_stored_student_report
from assessments.services.class_overview import (
    approve_class_students,
    get_class_teacher_assessment_detail,
    list_class_teacher_assessment_overview,
)
from assessments.services.workspace import (
    create_ca_item,
    delete_ca_item,
    get_workspace,
    publish_students,
    save_marks,
    unpublish_students,
    update_ca_item,
)
from shared.views import SchoolScopedAPIView


@extend_schema(
    tags=['Assessments'],
    summary='Subject assessment workspace',
    description=(
        'Markbook for a teaching assignment: CA items, student marks, '
        'level weights/bands, and computed class score / total / grade / status.'
    ),
    responses={200: AssessmentWorkspaceSerializer},
)
class TeachingAssignmentWorkspaceView(SchoolScopedAPIView):
    def get(self, request, assignment_id):
        payload = get_workspace(
            school=self.school,
            membership=self.membership,
            assignment_id=assignment_id,
        )
        return Response(AssessmentWorkspaceSerializer(payload).data)


@extend_schema(
    tags=['Assessments'],
    summary='Create class assessment (CA item)',
    request=CaItemWriteSerializer,
    responses={201: CaItemSerializer},
)
class TeachingAssignmentCaItemListView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.ASSESSMENTS_RECORD

    def post(self, request, assignment_id):
        serializer = CaItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = create_ca_item(
            school=self.school,
            membership=self.membership,
            assignment_id=assignment_id,
            name=serializer.validated_data['name'],
            max_marks=serializer.validated_data['max_marks'],
        )
        return Response(CaItemSerializer(payload).data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['Assessments'],
    summary='Update class assessment (CA item)',
    request=CaItemWriteSerializer,
    responses={200: CaItemSerializer},
)
class TeachingAssignmentCaItemDetailView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.ASSESSMENTS_RECORD

    def patch(self, request, assignment_id, item_id):
        serializer = CaItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = update_ca_item(
            school=self.school,
            membership=self.membership,
            assignment_id=assignment_id,
            item_id=item_id,
            name=serializer.validated_data['name'],
            max_marks=serializer.validated_data['max_marks'],
        )
        return Response(CaItemSerializer(payload).data)

    @extend_schema(summary='Delete class assessment (CA item)', responses={204: None})
    def delete(self, request, assignment_id, item_id):
        delete_ca_item(
            school=self.school,
            membership=self.membership,
            assignment_id=assignment_id,
            item_id=item_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=['Assessments'],
    summary='Save subject assessment marks',
    description=(
        'Bulk-save CA marks for all roster students (required) and optional exam marks. '
        'Returns the refreshed workspace payload.'
    ),
    request=SaveMarksSerializer,
    responses={200: AssessmentWorkspaceSerializer},
)
class TeachingAssignmentMarksView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.ASSESSMENTS_RECORD

    def put(self, request, assignment_id):
        serializer = SaveMarksSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = save_marks(
            school=self.school,
            membership=self.membership,
            assignment_id=assignment_id,
            students=serializer.validated_data['students'],
        )
        return Response(AssessmentWorkspaceSerializer(payload).data)


@extend_schema(
    tags=['Assessments'],
    summary='Publish subject results',
    request=PublishStudentsSerializer,
    responses={200: AssessmentWorkspaceSerializer},
)
class TeachingAssignmentPublishView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.ASSESSMENTS_RECORD

    def post(self, request, assignment_id):
        serializer = PublishStudentsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = publish_students(
            school=self.school,
            membership=self.membership,
            assignment_id=assignment_id,
            student_ids=serializer.validated_data['student_ids'],
        )
        return Response(AssessmentWorkspaceSerializer(payload).data)


@extend_schema(
    tags=['Assessments'],
    summary='Unpublish subject results',
    request=PublishStudentsSerializer,
    responses={200: AssessmentWorkspaceSerializer},
)
class TeachingAssignmentUnpublishView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.ASSESSMENTS_RECORD

    def post(self, request, assignment_id):
        serializer = PublishStudentsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = unpublish_students(
            school=self.school,
            membership=self.membership,
            assignment_id=assignment_id,
            student_ids=serializer.validated_data['student_ids'],
        )
        return Response(AssessmentWorkspaceSerializer(payload).data)


@extend_schema(
    tags=['Assessments'],
    summary='Admin assessment year and term filters',
    responses={200: AdminAssessmentFilterOptionsSerializer},
)
class AdminAssessmentFilterOptionsView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.ASSESSMENTS_RELEASE

    def get(self, request):
        payload = get_admin_assessment_filter_options(school=self.school)
        return Response(AdminAssessmentFilterOptionsSerializer(payload).data)


@extend_schema(
    tags=['Assessments'],
    summary='Admin assessment overview by class',
    responses={200: AdminAssessmentOverviewSerializer},
)
class AdminAssessmentOverviewView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.ASSESSMENTS_RELEASE

    def get(self, request):
        payload = list_admin_assessment_overview(
            school=self.school,
            term_id=request.query_params.get('term_id') or None,
        )
        return Response(AdminAssessmentOverviewSerializer(payload).data)


@extend_schema(
    tags=['Assessments'],
    summary='Admin assessment detail for a class',
    responses={200: AdminAssessmentDetailSerializer},
)
class AdminAssessmentDetailView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.ASSESSMENTS_RELEASE

    def get(self, request, stream_id):
        payload = get_admin_assessment_detail(
            school=self.school,
            stream_id=stream_id,
            term_id=request.query_params.get('term_id') or None,
        )
        return Response(AdminAssessmentDetailSerializer(payload).data)


@extend_schema(
    tags=['Assessments'],
    summary='Release approved students in a class',
    request=ApproveClassStudentsSerializer,
    responses={200: AdminAssessmentDetailSerializer},
)
class AdminAssessmentReleaseView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.ASSESSMENTS_RELEASE

    def post(self, request, stream_id):
        serializer = ApproveClassStudentsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = release_admin_students(
            school=self.school,
            membership=self.membership,
            stream_id=stream_id,
            student_ids=serializer.validated_data['student_ids'],
            remarks=serializer.validated_data.get('remarks', ''),
            term_id=request.query_params.get('term_id') or None,
        )
        return Response(AdminAssessmentDetailSerializer(payload).data)


@extend_schema(
    tags=['Assessments'],
    summary='Student report preview for a released assessment',
    responses={200: StudentReportPreviewSerializer},
)
class AdminStudentReportPreviewView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.ASSESSMENTS_RELEASE

    def get(self, request, stream_id, student_id):
        payload = get_student_report_preview(
            school=self.school,
            stream_id=stream_id,
            student_id=student_id,
            term_id=request.query_params.get('term_id') or None,
        )
        return Response(StudentReportPreviewSerializer(payload).data)


@extend_schema(
    tags=['Assessments'],
    summary='Get stored student report PDF (signed URL)',
    responses={200: StoredStudentReportSerializer},
)
class AdminStudentReportView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.ASSESSMENTS_RELEASE

    def get(self, request, stream_id, student_id):
        payload = get_stored_student_report(
            school=self.school,
            stream_id=stream_id,
            student_id=student_id,
            term_id=request.query_params.get('term_id') or None,
        )
        return Response(StoredStudentReportSerializer(payload).data)


@extend_schema(
    tags=['Assessments'],
    summary='Generate or overwrite student report PDF',
    responses={200: StoredStudentReportSerializer},
)
class AdminStudentReportGenerateView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.ASSESSMENTS_RELEASE

    def post(self, request, stream_id, student_id):
        payload = generate_student_report(
            school=self.school,
            membership=self.membership,
            stream_id=stream_id,
            student_id=student_id,
            term_id=request.query_params.get('term_id') or None,
        )
        return Response(StoredStudentReportSerializer(payload).data)


@extend_schema(
    tags=['Assessments'],
    summary='Class teacher assessment overview',
    responses={200: ClassTeacherAssessmentOverviewSerializer},
)
class ClassTeacherAssessmentOverviewView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.NAV_ASSESSMENTS

    def get(self, request):
        payload = list_class_teacher_assessment_overview(
            school=self.school,
            membership=self.membership,
        )
        return Response(ClassTeacherAssessmentOverviewSerializer(payload).data)


@extend_schema(
    tags=['Assessments'],
    summary='Class teacher assessment detail',
    responses={200: ClassTeacherAssessmentDetailSerializer},
)
class ClassTeacherAssessmentDetailView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.NAV_ASSESSMENTS

    def get(self, request, class_teacher_id):
        payload = get_class_teacher_assessment_detail(
            school=self.school,
            membership=self.membership,
            class_teacher_id=class_teacher_id,
        )
        return Response(ClassTeacherAssessmentDetailSerializer(payload).data)


@extend_schema(
    tags=['Assessments'],
    summary='Approve students for a managed class',
    request=ApproveClassStudentsSerializer,
    responses={200: ClassTeacherAssessmentDetailSerializer},
)
class ClassTeacherApproveStudentsView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.ASSESSMENTS_APPROVE

    def post(self, request, class_teacher_id):
        serializer = ApproveClassStudentsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = approve_class_students(
            school=self.school,
            membership=self.membership,
            class_teacher_id=class_teacher_id,
            student_ids=serializer.validated_data['student_ids'],
            remarks=serializer.validated_data.get('remarks', ''),
            conduct=serializer.validated_data.get('conduct', ''),
            attitude=serializer.validated_data.get('attitude', ''),
            interest=serializer.validated_data.get('interest', ''),
        )
        return Response(ClassTeacherAssessmentDetailSerializer(payload).data)


@extend_schema(
    tags=['Assessments'],
    summary='Admin reject or reopen selected subjects for a student',
    request=CorrectionActionSerializer,
    responses={200: CorrectionActionResponseSerializer},
)
class AdminStudentCorrectionView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.ASSESSMENTS_RELEASE

    def post(self, request, stream_id, student_id):
        serializer = CorrectionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = reject_or_reopen_student(
            school=self.school,
            membership=self.membership,
            stream_id=stream_id,
            student_id=student_id,
            teaching_assignment_ids=serializer.validated_data['teaching_assignment_ids'],
            reason=serializer.validated_data['reason'],
            term_id=request.query_params.get('term_id') or None,
        )
        return Response({
            'correction': payload['correction'],
            'detail': AdminAssessmentDetailSerializer(payload['detail']).data,
        })


@extend_schema(
    tags=['Assessments'],
    summary='Admin approve or decline a reopen request',
    request=CorrectionReviewSerializer,
    responses={200: CorrectionActionResponseSerializer},
)
class AdminCorrectionReviewView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.ASSESSMENTS_RELEASE

    def post(self, request, stream_id, correction_id):
        serializer = CorrectionReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = review_reopen_request(
            school=self.school,
            membership=self.membership,
            stream_id=stream_id,
            correction_id=correction_id,
            approve=serializer.validated_data['approve'],
            term_id=request.query_params.get('term_id') or None,
        )
        return Response({
            'correction': payload['correction'],
            'detail': AdminAssessmentDetailSerializer(payload['detail']).data,
        })


@extend_schema(
    tags=['Assessments'],
    summary='Class teacher reject selected subjects (pre-release)',
    request=CorrectionActionSerializer,
    responses={200: CorrectionActionResponseSerializer},
)
class ClassTeacherRejectStudentView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.ASSESSMENTS_APPROVE

    def post(self, request, class_teacher_id, student_id):
        serializer = CorrectionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = reject_class_teacher_student(
            school=self.school,
            membership=self.membership,
            class_teacher_id=class_teacher_id,
            student_id=student_id,
            teaching_assignment_ids=serializer.validated_data['teaching_assignment_ids'],
            reason=serializer.validated_data['reason'],
        )
        return Response({
            'correction': payload['correction'],
            'detail': ClassTeacherAssessmentDetailSerializer(payload['detail']).data,
        })


@extend_schema(
    tags=['Assessments'],
    summary='Class teacher request reopen after release',
    request=CorrectionActionSerializer,
    responses={200: CorrectionActionResponseSerializer},
)
class ClassTeacherRequestReopenView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.ASSESSMENTS_APPROVE

    def post(self, request, class_teacher_id, student_id):
        serializer = CorrectionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = request_reopen_student(
            school=self.school,
            membership=self.membership,
            class_teacher_id=class_teacher_id,
            student_id=student_id,
            teaching_assignment_ids=serializer.validated_data['teaching_assignment_ids'],
            reason=serializer.validated_data['reason'],
        )
        return Response({
            'correction': payload['correction'],
            'detail': ClassTeacherAssessmentDetailSerializer(payload['detail']).data,
        })
