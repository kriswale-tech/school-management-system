from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from core.pagination import StandardResultsSetPagination, paginated_schema
from shared.views import SchoolScopedAPIView
from schools.services.teachers import (
    complete_teachers_setup,
    create_class_teacher_assignment,
    create_teaching_assignment,
    delete_class_teacher_assignment,
    delete_teaching_assignment,
    get_teachers_setup_queryset,
    serialize_teacher_for_setup,
)
from schools.setup_serializers.common import SetupStepResponseSerializer
from schools.setup_serializers.teachers import (
    CreateClassTeacherAssignmentSerializer,
    CreateTeachingAssignmentSerializer,
    SetupClassTeacherAssignmentSerializer,
    SetupTeacherSerializer,
    SetupTeachingAssignmentSerializer,
)


@extend_schema(
    summary='Get teachers setup',
    description=(
        'Returns a paginated list of active teachers in the school with profile '
        'details and assignments for the current active term.'
    ),
    responses={
        200: paginated_schema(SetupTeacherSerializer, name='PaginatedSetupTeacherList'),
    },
)
class SetupTeachersView(SchoolScopedAPIView):
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        teachers = get_teachers_setup_queryset(self.school)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(teachers, request)
        data = [serialize_teacher_for_setup(teacher) for teacher in page]
        serializer = SetupTeacherSerializer(data, many=True)
        return paginator.get_paginated_response(serializer.data)


@extend_schema(
    summary='Create class teacher assignment',
    description=(
        'Assigns a teacher as class teacher for the active term. '
        'Omit stream_id or send null to cover the whole class.'
    ),
    request=CreateClassTeacherAssignmentSerializer,
    responses={201: SetupClassTeacherAssignmentSerializer},
)
class SetupClassTeacherAssignmentCreateView(SchoolScopedAPIView):
    def post(self, request):
        serializer = CreateClassTeacherAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = create_class_teacher_assignment(
            self.school,
            **serializer.validated_data,
        )
        return Response(
            SetupClassTeacherAssignmentSerializer(data).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    summary='Delete class teacher assignment',
    description='Removes a class teacher assignment for the active term.',
    responses={204: None},
)
class SetupClassTeacherAssignmentDetailView(SchoolScopedAPIView):
    def delete(self, request, assignment_id):
        delete_class_teacher_assignment(
            self.school,
            assignment_id=assignment_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    summary='Create teaching assignment',
    description=(
        'Assigns a teacher to teach a class subject for the active term. '
        'Optionally scope the assignment to a stream and/or subject group.'
    ),
    request=CreateTeachingAssignmentSerializer,
    responses={201: SetupTeachingAssignmentSerializer},
)
class SetupTeachingAssignmentCreateView(SchoolScopedAPIView):
    def post(self, request):
        serializer = CreateTeachingAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = create_teaching_assignment(
            self.school,
            **serializer.validated_data,
        )
        return Response(
            SetupTeachingAssignmentSerializer(data).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    summary='Delete teaching assignment',
    description='Removes a teaching assignment for the active term.',
    responses={204: None},
)
class SetupTeachingAssignmentDetailView(SchoolScopedAPIView):
    def delete(self, request, assignment_id):
        delete_teaching_assignment(
            self.school,
            assignment_id=assignment_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    summary='Complete teachers setup',
    description=(
        'Validates that the school has at least one active teacher for the '
        'current term context, then advances setup to the next step.'
    ),
    request=None,
    responses={200: SetupStepResponseSerializer},
)
class CompleteTeachersSetupView(SchoolScopedAPIView):
    def post(self, request):
        result = complete_teachers_setup(self.school)
        return Response(SetupStepResponseSerializer(result).data)
