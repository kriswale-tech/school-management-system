from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from accounts.capabilities import Capability
from accounts.permissions import HasActiveSchool, HasCapability
from billing.models import SchoolSubscription
from billing.serializers import SubscriptionSerializer
from communications.models import CommunicationAddonSku, CreditLedgerEntry
from communications.serializers import (
    CommunicationAddonSkuSerializer,
    CreditBalancesSerializer,
    CreditLedgerEntrySerializer,
    ScheduleAddonChangeSerializer,
)
from communications.services.addons import schedule_addon_change
from communications.services.gates import communications_billing_active
from communications.services.ledger import get_balances
from core.pagination import StandardResultsSetPagination
from shared.views import SchoolScopedAPIView


class SchoolAddonSkuCatalogView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.BILLING_VIEW

    @extend_schema(responses={200: CommunicationAddonSkuSerializer(many=True)})
    def get(self, request):
        from billing.services.capacity import current_subscription

        subscription = current_subscription(self.school)
        if subscription is None or subscription.plan_id is None:
            return Response([])

        qs = (
            CommunicationAddonSku.objects.filter(
                is_active=True,
                available_plans=subscription.plan,
            )
            .distinct()
            .order_by('channel', 'interval', 'sort_order')
        )
        interval = (request.query_params.get('interval') or '').strip()
        if interval:
            qs = qs.filter(interval=interval)
        else:
            qs = qs.filter(interval=subscription.interval)
        return Response(CommunicationAddonSkuSerializer(qs, many=True).data)


class SchoolCreditsView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.BILLING_VIEW

    @extend_schema(responses={200: CreditBalancesSerializer})
    def get(self, request):
        balances = get_balances(self.school)
        return Response({
            'sms': balances.get('sms', 0),
            'email': balances.get('email', 0),
            'billing_active': communications_billing_active(self.school),
        })


class SchoolLedgerView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.BILLING_VIEW
    pagination_class = StandardResultsSetPagination

    @extend_schema(responses={200: CreditLedgerEntrySerializer(many=True)})
    def get(self, request):
        qs = CreditLedgerEntry.objects.filter(school=self.school).order_by('-occurred_at')
        channel = (request.query_params.get('channel') or '').strip()
        if channel:
            qs = qs.filter(channel=channel)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(
            CreditLedgerEntrySerializer(page, many=True).data,
        )


class SchoolAddonScheduleView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.BILLING_MANAGE

    @extend_schema(request=ScheduleAddonChangeSerializer, responses={200: SubscriptionSerializer})
    def post(self, request):
        serializer = ScheduleAddonChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        sku = None
        if data['enabled'] and data.get('sku_code'):
            sku = CommunicationAddonSku.objects.filter(
                code=data['sku_code'],
                is_active=True,
            ).first()
            if sku is None:
                raise ValidationError({'sku_code': 'Unknown or inactive SKU.'})
        subscription = schedule_addon_change(
            school=self.school,
            channel=data['channel'],
            enabled=data['enabled'],
            sku=sku,
            actor=None,
        )
        subscription = (
            SchoolSubscription.objects.filter(pk=subscription.pk)
            .select_related(
                'plan',
                'pending_plan',
                'sms_sku',
                'email_sku',
                'pending_sms_sku',
                'pending_email_sku',
            )
            .get()
        )
        return Response(SubscriptionSerializer(subscription).data)
