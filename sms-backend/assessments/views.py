from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from accounts.capabilities import Capability
from accounts.permissions import HasActiveSchool, HasCapability
from assessments.serializers import (
    ApproveClassStudentsSerializer,
    AssessmentWorkspaceSerializer,
    CaItemSerializer,
    CaItemWriteSerializer,
    ClassTeacherAssessmentDetailSerializer,
    ClassTeacherAssessmentOverviewSerializer,
    PublishStudentsSerializer,
    SaveMarksSerializer,
)
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
        )
        return Response(ClassTeacherAssessmentDetailSerializer(payload).data)
