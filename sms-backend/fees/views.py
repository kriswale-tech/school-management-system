from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.pagination import StandardResultsSetPagination, paginated_schema
from fees.serializers import (
    CreateFeeStructureItemSerializer,
    FeeDeskFilterOptionsSerializer,
    FeeDeskRowSerializer,
    FeeDeskStatsSerializer,
    FeeItemSettingsSerializer,
    FeeStructureDetailSerializer,
    RecordPaymentResponseSerializer,
    RecordPaymentSerializer,
    StudentPaymentTargetSerializer,
    UpdateFeeStructureItemSerializer,
)
from fees.services.desk import (
    get_fee_desk_stats,
    get_fee_filter_options,
    list_fee_desk_rows,
    resolve_fee_desk_term,
)
from fees.services.payments import build_student_payment_target, record_student_payment
from fees.services.settings import (
    apply_structure,
    create_fee_item,
    delete_fee_item,
    get_fee_structure_detail,
    update_fee_item,
)
from shared.views import SchoolScopedAPIView
from students.filters import StudentEnrollmentFilter
from students.services import get_student


def _filtered_fee_desk_queryset(request, school):
    term = resolve_fee_desk_term(school, request.query_params.get('term'))
    queryset = list_fee_desk_rows(school=school, term=term)
    filterset = StudentEnrollmentFilter(request.query_params, queryset=queryset)
    if not filterset.is_valid():
        raise ValidationError(filterset.errors)
    return term, filterset.qs


class FeeDeskListView(SchoolScopedAPIView):
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        tags=['Fees'],
        summary='List student fee balances',
        description=(
            'Paginated fees desk rows for students enrolled in the selected term. '
            'Defaults to the school active term. Supports search and class filters.'
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
                description='Term UUID. Defaults to the school active term.',
            ),
            OpenApiParameter(name='page', type=int, description='Page number.'),
            OpenApiParameter(name='page_size', type=int, description='Page size (max 100).'),
        ],
        responses={
            200: paginated_schema(FeeDeskRowSerializer, name='PaginatedFeeDeskList'),
        },
    )
    def get(self, request):
        _term, queryset = _filtered_fee_desk_queryset(request, self.school)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = FeeDeskRowSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class FeeDeskStatsView(SchoolScopedAPIView):
    @extend_schema(
        tags=['Fees'],
        summary='Fees desk statistics',
        description=(
            'Aggregate fee totals for the filtered enrollment set. '
            'Uses the same filters as the fees desk list.'
        ),
        parameters=[
            OpenApiParameter(name='search', type=str),
            OpenApiParameter(name='class_level', type=str),
            OpenApiParameter(name='stream', type=str),
            OpenApiParameter(
                name='term',
                type=str,
                description='Term UUID. Defaults to the school active term.',
            ),
        ],
        responses={200: FeeDeskStatsSerializer},
    )
    def get(self, request):
        _term, queryset = _filtered_fee_desk_queryset(request, self.school)
        stats = get_fee_desk_stats(queryset=queryset)
        return Response(FeeDeskStatsSerializer(stats).data)


class FeeDeskFilterOptionsView(SchoolScopedAPIView):
    @extend_schema(
        tags=['Fees'],
        summary='Fees desk filter options',
        description='Academic years and terms for fees desk filters, including the active term.',
        responses={200: FeeDeskFilterOptionsSerializer},
    )
    def get(self, request):
        data = get_fee_filter_options(school=self.school)
        return Response(FeeDeskFilterOptionsSerializer(data).data)


class StudentPaymentTargetView(SchoolScopedAPIView):
    @extend_schema(
        tags=['Fees'],
        summary='Student payment target',
        description=(
            'Returns the earliest term with an outstanding balance for a student, '
            'plus summary fields for the record-payment form.'
        ),
        responses={200: StudentPaymentTargetSerializer},
    )
    def get(self, request, student_id):
        student = get_student(school=self.school, student_id=student_id)
        data = build_student_payment_target(school=self.school, student=student)
        return Response(StudentPaymentTargetSerializer(data).data)


class RecordPaymentView(SchoolScopedAPIView):
    @extend_schema(
        tags=['Fees'],
        summary='Record a student fee payment',
        description=(
            'Records a payment against the earliest term with an outstanding balance. '
            'Issues a receipt automatically.'
        ),
        request=RecordPaymentSerializer,
        responses={201: RecordPaymentResponseSerializer},
    )
    def post(self, request):
        serializer = RecordPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = get_student(
            school=self.school,
            student_id=serializer.validated_data['student_id'],
        )
        try:
            result = record_student_payment(
                school=self.school,
                student=student,
                amount=serializer.validated_data['amount'],
                payment_method=serializer.validated_data['payment_method'],
                paid_at=serializer.validated_data['paid_at'],
                payment_reference=serializer.validated_data.get('payment_reference', ''),
                payment_notes=serializer.validated_data.get('payment_notes', ''),
                recorded_by=request.user,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict)

        return Response(
            RecordPaymentResponseSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )


class FeeStructureDetailView(SchoolScopedAPIView):
    @extend_schema(
        tags=['Fees'],
        summary='Get fee structure for a term',
        description=(
            'Returns the fee structure and items for a term, creating or carrying '
            'forward a catalog if one does not exist. Defaults to the active term.'
        ),
        parameters=[
            OpenApiParameter(
                name='term',
                type=str,
                description='Term UUID. Defaults to the school active term.',
            ),
        ],
        responses={200: FeeStructureDetailSerializer},
    )
    def get(self, request):
        data = get_fee_structure_detail(
            school=self.school,
            created_by=request.user,
            term_id=request.query_params.get('term'),
        )
        return Response(FeeStructureDetailSerializer(data).data)


class FeeStructureItemCreateView(SchoolScopedAPIView):
    @extend_schema(
        tags=['Fees'],
        summary='Create a fee item',
        description=(
            'Adds a fee item to the selected term structure while it is still editable. '
            'Term defaults to the school active term.'
        ),
        request=CreateFeeStructureItemSerializer,
        responses={201: FeeItemSettingsSerializer},
    )
    def post(self, request):
        serializer = CreateFeeStructureItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)
        term_id = payload.pop('term', None)
        data = create_fee_item(
            self.school,
            created_by=request.user,
            term_id=term_id,
            **payload,
        )
        return Response(FeeItemSettingsSerializer(data).data, status=status.HTTP_201_CREATED)


class FeeStructureItemDetailView(SchoolScopedAPIView):
    @extend_schema(
        methods=['PATCH'],
        tags=['Fees'],
        summary='Update a fee item',
        description='Updates a fee item while its term structure is still editable.',
        request=UpdateFeeStructureItemSerializer,
        responses={200: FeeItemSettingsSerializer},
    )
    @extend_schema(
        methods=['DELETE'],
        tags=['Fees'],
        summary='Delete a fee item',
        description='Removes a fee item while its term structure is still editable.',
        responses={204: None},
    )
    def patch(self, request, fee_item_id):
        serializer = UpdateFeeStructureItemSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = update_fee_item(
            self.school,
            fee_item_id=fee_item_id,
            **serializer.validated_data,
        )
        return Response(FeeItemSettingsSerializer(data).data)

    def delete(self, request, fee_item_id):
        delete_fee_item(self.school, fee_item_id=fee_item_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApplyFeeStructureView(SchoolScopedAPIView):
    @extend_schema(
        tags=['Fees'],
        summary='Apply a fee structure',
        description=(
            'Publishes a draft if needed, then bills currently enrolled students '
            'and locks the catalog for that term. Later enrollments are billed automatically.'
        ),
        request=None,
        responses={200: FeeStructureDetailSerializer},
    )
    def post(self, request, structure_id):
        data = apply_structure(school=self.school, structure_id=structure_id)
        return Response(FeeStructureDetailSerializer(data).data)
