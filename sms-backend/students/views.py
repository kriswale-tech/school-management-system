from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.pagination import StandardResultsSetPagination, paginated_schema
from shared.views import SchoolScopedAPIView
from students.filters import ParentFilter, StudentEnrollmentFilter
from students.serializers import (
    ParentListSerializer,
    StudentListSerializer,
    StudentOnboardSerializer,
    StudentStatsSerializer,
)
from students.services import (
    get_student_stats,
    list_enrollments_for_term,
    list_parents_for_school,
    onboard_student,
    resolve_term,
)


class StudentListView(SchoolScopedAPIView):
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        tags=['Students'],
        summary='List students',
        description=(
            'Returns paginated students enrolled in the active term for the '
            'selected school. Supports search, class-level, and stream filtering.'
        ),
        parameters=[
            OpenApiParameter(
                name='search',
                type=str,
                description='Search student ID, first name, last name, or other names.',
            ),
            OpenApiParameter(
                name='class_level',
                type=str,
                description='Filter by class level UUID.',
            ),
            OpenApiParameter(
                name='stream',
                type=str,
                description='Filter by class stream UUID.',
            ),
            OpenApiParameter(
                name='term',
                type=str,
                description='Optional term UUID. Defaults to the school active term.',
            ),
            OpenApiParameter(name='page', type=int, description='Page number.'),
            OpenApiParameter(name='page_size', type=int, description='Page size (max 100).'),
        ],
        responses={
            200: paginated_schema(StudentListSerializer, name='PaginatedStudentList'),
        },
    )
    def get(self, request):
        term = resolve_term(self.school, request.query_params.get('term'))
        queryset = list_enrollments_for_term(school=self.school, term=term)
        filterset = StudentEnrollmentFilter(request.query_params, queryset=queryset)
        if not filterset.is_valid():
            raise ValidationError(filterset.errors)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = StudentListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class ParentListView(SchoolScopedAPIView):
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        tags=['Students'],
        summary='List parents',
        description=(
            'Returns paginated parents for the selected school. '
            'Supports search by name, phone number, or email.'
        ),
        parameters=[
            OpenApiParameter(
                name='search',
                type=str,
                description='Search parent name, phone number, or email.',
            ),
            OpenApiParameter(name='page', type=int, description='Page number.'),
            OpenApiParameter(name='page_size', type=int, description='Page size (max 100).'),
        ],
        responses={
            200: paginated_schema(ParentListSerializer, name='PaginatedParentList'),
        },
    )
    def get(self, request):
        queryset = list_parents_for_school(school=self.school)
        filterset = ParentFilter(request.query_params, queryset=queryset)
        if not filterset.is_valid():
            raise ValidationError(filterset.errors)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = ParentListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class StudentOnboardView(SchoolScopedAPIView):
    @extend_schema(
        tags=['Students'],
        summary='Onboard student',
        description=(
            'Creates a student with guardians and enrolls them in a stream for the '
            'active term. student_id is auto-generated from school initials. '
            'Each guardian may be a new parent (name + phone) or an existing parent '
            '(parent_id). The first guardian in the array is the primary contact.'
        ),
        request=StudentOnboardSerializer,
        responses={201: StudentListSerializer},
    )
    def post(self, request):
        serializer = StudentOnboardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enrollment = onboard_student(school=self.school, **serializer.validated_data)
        return Response(
            StudentListSerializer(enrollment).data,
            status=status.HTTP_201_CREATED,
        )


class StudentStatsView(SchoolScopedAPIView):
    @extend_schema(
        tags=['Students'],
        summary='Student statistics',
        description=(
            'Returns summary counts for students enrolled in the active term, '
            'including gender, new vs continuing, and fee payment status.'
        ),
        parameters=[
            OpenApiParameter(
                name='term',
                type=str,
                description='Optional term UUID. Defaults to the school active term.',
            ),
        ],
        responses={200: StudentStatsSerializer},
    )
    def get(self, request):
        term = resolve_term(self.school, request.query_params.get('term'))
        stats = get_student_stats(school=self.school, term=term)
        return Response(StudentStatsSerializer(stats).data)
