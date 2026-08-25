from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.pagination import StandardResultsSetPagination, paginated_schema
from fees.services import get_student_fee_history, get_student_fees, list_student_payments
from shared.views import SchoolScopedAPIView
from students.filters import ParentFilter, StudentEnrollmentFilter
from students.serializers import (
    GuardianCreateSerializer,
    GuardianUpdateSerializer,
    ParentListSerializer,
    StudentDetailSerializer,
    StudentFeeHistorySerializer,
    StudentGuardianSerializer,
    StudentListSerializer,
    StudentOnboardSerializer,
    StudentPaymentSerializer,
    StudentStatsSerializer,
    StudentUpdateSerializer,
    StudentYearFeesSerializer,
)
from students.services import (
    add_student_guardian,
    build_student_detail,
    get_student,
    get_student_stats,
    list_enrollments_for_term,
    list_parents_for_school,
    list_student_guardians,
    onboard_student,
    remove_student_guardian,
    resolve_term,
    update_student,
    update_student_guardian,
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


class StudentDetailView(SchoolScopedAPIView):
    @extend_schema(
        tags=['Students'],
        summary='Get student detail',
        description=(
            'Returns full student profile for the selected school, including age, '
            'active-term class assignment, is_active, is_new_student, and guardians.'
        ),
        responses={200: StudentDetailSerializer},
    )
    def get(self, request, student_id):
        student = get_student(school=self.school, student_id=student_id)
        detail = build_student_detail(school=self.school, student=student)
        return Response(StudentDetailSerializer(detail).data)

    @extend_schema(
        tags=['Students'],
        summary='Update student profile',
        description=(
            'Partially updates editable student profile fields. '
            'student_id, age, is_new_student, and class assignment are not editable here.'
        ),
        request=StudentUpdateSerializer,
        responses={200: StudentDetailSerializer},
    )
    def patch(self, request, student_id):
        serializer = StudentUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        detail = update_student(
            school=self.school,
            student_id=student_id,
            **serializer.validated_data,
        )
        return Response(StudentDetailSerializer(detail).data)


class StudentGuardianListCreateView(SchoolScopedAPIView):
    @extend_schema(
        tags=['Students'],
        summary='List student guardians',
        responses={200: StudentGuardianSerializer(many=True)},
    )
    def get(self, request, student_id):
        guardians = list_student_guardians(school=self.school, student_id=student_id)
        return Response(StudentGuardianSerializer(guardians, many=True).data)

    @extend_schema(
        tags=['Students'],
        summary='Add student guardian',
        request=GuardianCreateSerializer,
        responses={201: StudentGuardianSerializer},
    )
    def post(self, request, student_id):
        serializer = GuardianCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        guardian = add_student_guardian(
            school=self.school,
            student_id=student_id,
            guardian=serializer.validated_data,
        )
        return Response(
            StudentGuardianSerializer(guardian).data,
            status=status.HTTP_201_CREATED,
        )


class StudentGuardianDetailView(SchoolScopedAPIView):
    @extend_schema(
        tags=['Students'],
        summary='Update student guardian',
        description=(
            'Updates the guardian association and/or shared parent contact fields '
            'within this school. Use is_primary=true to promote this guardian.'
        ),
        request=GuardianUpdateSerializer,
        responses={200: StudentGuardianSerializer},
    )
    def patch(self, request, student_id, link_id):
        serializer = GuardianUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        guardian = update_student_guardian(
            school=self.school,
            student_id=student_id,
            link_id=link_id,
            **serializer.validated_data,
        )
        return Response(StudentGuardianSerializer(guardian).data)

    @extend_schema(
        tags=['Students'],
        summary='Remove student guardian association',
        description=(
            'Removes the StudentParent link only. Cannot remove the last guardian. '
            'If the primary is removed, another guardian is silently promoted.'
        ),
        responses={204: None},
    )
    def delete(self, request, student_id, link_id):
        remove_student_guardian(
            school=self.school,
            student_id=student_id,
            link_id=link_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class StudentCurrentYearFeesView(SchoolScopedAPIView):
    @extend_schema(
        tags=['Students'],
        summary='Student fee breakdown',
        description=(
            'Returns fee breakdown for an academic year (defaults to the active year). '
            'Optional term filter scopes totals and term rows to that term.'
        ),
        parameters=[
            OpenApiParameter(
                name='academic_year',
                type=str,
                description='Optional academic year UUID.',
            ),
            OpenApiParameter(
                name='term',
                type=str,
                description='Optional term UUID. When set, only that term is included.',
            ),
        ],
        responses={200: StudentYearFeesSerializer},
    )
    def get(self, request, student_id):
        student = get_student(school=self.school, student_id=student_id)
        data = get_student_fees(
            school=self.school,
            student=student,
            academic_year_id=request.query_params.get('academic_year'),
            term_id=request.query_params.get('term'),
        )
        return Response(StudentYearFeesSerializer(data).data)


class StudentPaymentListView(SchoolScopedAPIView):
    @extend_schema(
        tags=['Students'],
        summary='Student payment history',
        description=(
            'Returns payment ledger rows for a student. '
            'Filter by academic year or term when provided.'
        ),
        parameters=[
            OpenApiParameter(
                name='academic_year',
                type=str,
                description='Optional academic year UUID.',
            ),
            OpenApiParameter(
                name='term',
                type=str,
                description='Optional term UUID.',
            ),
        ],
        responses={200: StudentPaymentSerializer(many=True)},
    )
    def get(self, request, student_id):
        student = get_student(school=self.school, student_id=student_id)
        rows = list_student_payments(
            school=self.school,
            student=student,
            academic_year_id=request.query_params.get('academic_year'),
            term_id=request.query_params.get('term'),
        )
        return Response(StudentPaymentSerializer(rows, many=True).data)


class StudentFeeHistoryView(SchoolScopedAPIView):
    @extend_schema(
        tags=['Students'],
        summary='Student fee history',
        description=(
            'Returns academic years that have fee or payment data for this student. '
            'Optionally filter to a single academic year UUID.'
        ),
        parameters=[
            OpenApiParameter(
                name='academic_year',
                type=str,
                description='Optional academic year UUID. Only years with data are returned.',
            ),
        ],
        responses={200: StudentFeeHistorySerializer},
    )
    def get(self, request, student_id):
        student = get_student(school=self.school, student_id=student_id)
        data = get_student_fee_history(
            school=self.school,
            student=student,
            academic_year_id=request.query_params.get('academic_year'),
        )
        return Response(StudentFeeHistorySerializer(data).data)
