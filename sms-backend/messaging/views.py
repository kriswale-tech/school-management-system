from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework import status
from rest_framework.response import Response

from accounts.capabilities import Capability
from accounts.permissions import HasActiveSchool, HasCapability
from core.pagination import StandardResultsSetPagination
from messaging.serializers import (
    BulkRetryDeliverySerializer,
    EligibleResendSelectionSerializer,
    GuardianDeliverySerializer,
    MessageTemplatePreviewSerializer,
    MessageTemplateSerializer,
    MessageTemplateUpdateSerializer,
    MessagingOverviewSerializer,
    RetryDeliverySerializer,
    VerifyDeliverySerializer,
)
from messaging.services import (
    apply_delivery_filters,
    delivery_queryset,
    eligible_resend_selection,
    messaging_overview,
    retry_guardian_deliveries,
    retry_guardian_delivery,
    verify_guardian_delivery,
)
from notifications.services.message_templates import (
    list_templates_for_school,
    preview_template,
    upsert_template,
)
from shared.views import SchoolScopedAPIView


class MessagingOverviewView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.MESSAGING_VIEW

    @extend_schema(responses={200: MessagingOverviewSerializer})
    def get(self, request):
        start_raw = (request.query_params.get('start') or '').strip()
        end_raw = (request.query_params.get('end') or '').strip()
        start_date = parse_date(start_raw) if start_raw else None
        end_date = parse_date(end_raw) if end_raw else None
        if start_raw and start_date is None:
            raise ValidationError({'start': 'Use a date in YYYY-MM-DD format.'})
        if end_raw and end_date is None:
            raise ValidationError({'end': 'Use a date in YYYY-MM-DD format.'})
        if start_date or end_date:
            return Response(
                messaging_overview(self.school, start_date=start_date, end_date=end_date),
            )
        period = (request.query_params.get('period') or '7d').strip().lower()
        return Response(messaging_overview(self.school, period=period))


class MessagingDeliveryListView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.MESSAGING_VIEW
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        parameters=[
            OpenApiParameter('channel', str, required=False),
            OpenApiParameter('status', str, required=False),
            OpenApiParameter('event_type', str, required=False),
            OpenApiParameter('search', str, required=False),
        ],
        responses={200: GuardianDeliverySerializer(many=True)},
    )
    def get(self, request):
        qs = apply_delivery_filters(
            delivery_queryset(self.school),
            channel=(request.query_params.get('channel') or '').strip(),
            status=(request.query_params.get('status') or '').strip(),
            event_type=(request.query_params.get('event_type') or '').strip(),
            search=(request.query_params.get('search') or '').strip(),
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(
            GuardianDeliverySerializer(page, many=True).data,
        )


class MessagingDeliveryEligibleView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.MESSAGING_MANAGE

    @extend_schema(
        parameters=[
            OpenApiParameter('channel', str, required=False),
            OpenApiParameter('status', str, required=False),
            OpenApiParameter('event_type', str, required=False),
            OpenApiParameter('search', str, required=False),
        ],
        responses={200: EligibleResendSelectionSerializer},
    )
    def get(self, request):
        selection = eligible_resend_selection(
            self.school,
            channel=(request.query_params.get('channel') or '').strip(),
            status=(request.query_params.get('status') or '').strip(),
            event_type=(request.query_params.get('event_type') or '').strip(),
            search=(request.query_params.get('search') or '').strip(),
        )
        return Response(EligibleResendSelectionSerializer(selection).data)


class MessagingDeliveryBulkRetryView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.MESSAGING_MANAGE

    @extend_schema(request=BulkRetryDeliverySerializer)
    def post(self, request):
        serializer = BulkRetryDeliverySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = retry_guardian_deliveries(
            school=self.school,
            delivery_ids=serializer.validated_data['ids'],
        )
        return Response(result, status=status.HTTP_200_OK)


class MessagingDeliveryRetryView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.MESSAGING_MANAGE

    @extend_schema(responses={200: RetryDeliverySerializer})
    def post(self, request, pk):
        result = retry_guardian_delivery(school=self.school, delivery_id=pk)
        return Response(result, status=status.HTTP_200_OK)


class MessagingDeliveryVerifyView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.MESSAGING_MANAGE

    @extend_schema(responses={200: VerifyDeliverySerializer})
    def post(self, request, pk):
        result = verify_guardian_delivery(school=self.school, delivery_id=pk)
        return Response(result, status=status.HTTP_200_OK)


class MessagingTemplateListView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.MESSAGING_VIEW

    @extend_schema(responses={200: MessageTemplateSerializer(many=True)})
    def get(self, request):
        return Response(list_templates_for_school(self.school))


class MessagingTemplateUpdateView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.MESSAGING_MANAGE

    @extend_schema(
        request=MessageTemplateUpdateSerializer,
        responses={200: MessageTemplateSerializer(many=True)},
    )
    def put(self, request):
        serializer = MessageTemplateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        upsert_template(
            school=self.school,
            event_type=data['event_type'],
            sms_body=data.get('sms_body'),
            sms_body_all_time=data.get('sms_body_all_time'),
            email_subject=data.get('email_subject'),
            email_text=data.get('email_text'),
            email_html=data.get('email_html'),
            restore=data.get('restore'),
        )
        return Response(list_templates_for_school(self.school))


class MessagingTemplatePreviewView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.MESSAGING_VIEW

    @extend_schema(request=MessageTemplatePreviewSerializer)
    def post(self, request):
        serializer = MessageTemplatePreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = preview_template(
            school=self.school,
            event_type=data['event_type'],
            channel=data['channel'],
            sms_body=data.get('sms_body'),
            sms_body_all_time=data.get('sms_body_all_time'),
            email_subject=data.get('email_subject'),
            email_text=data.get('email_text'),
            all_time=bool(data.get('all_time')),
        )
        return Response(result)
