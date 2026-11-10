from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.models import SchoolSubscription
from billing.serializers import SubscriptionSerializer
from communications.models import CommunicationAddonSku, CreditLedgerEntry
from communications.serializers import (
    CommunicationAddonSkuSerializer,
    CommunicationAddonSkuWriteSerializer,
    CreditBalancesSerializer,
    CreditLedgerEntrySerializer,
    ManualCreditAdjustSerializer,
    ScheduleAddonChangeSerializer,
)
from communications.services.addons import schedule_addon_change
from communications.services.catalog import seed_default_skus
from communications.services.gates import communications_billing_active
from communications.services.ledger import get_balances, manual_adjust
from core.pagination import StandardResultsSetPagination
from platform_admin.authentication import PlatformJWTCookieAuthentication
from platform_admin.permissions import IsPlatformAuthenticated
from platform_admin.utils import client_ip
from schools.models import School


def _school_or_404(pk) -> School:
    school = School.objects.filter(pk=pk).first()
    if school is None:
        raise NotFound('School not found.')
    return school


class PlatformAddonSkuListCreateView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(responses={200: CommunicationAddonSkuSerializer(many=True)})
    def get(self, request):
        qs = (
            CommunicationAddonSku.objects.all()
            .prefetch_related('available_plans')
            .order_by('channel', 'interval', 'sort_order')
        )
        return Response(CommunicationAddonSkuSerializer(qs, many=True).data)

    @extend_schema(
        request=CommunicationAddonSkuWriteSerializer,
        responses={201: CommunicationAddonSkuSerializer},
    )
    def post(self, request):
        serializer = CommunicationAddonSkuWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sku = serializer.save()
        return Response(
            CommunicationAddonSkuSerializer(sku).data,
            status=status.HTTP_201_CREATED,
        )


# Backward-compatible alias.
PlatformAddonSkuListView = PlatformAddonSkuListCreateView


class PlatformAddonSkuDetailView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    def _get(self, pk) -> CommunicationAddonSku:
        sku = CommunicationAddonSku.objects.filter(pk=pk).first()
        if sku is None:
            raise NotFound('Addon SKU not found.')
        return sku

    @extend_schema(responses={200: CommunicationAddonSkuSerializer})
    def get(self, request, pk):
        return Response(CommunicationAddonSkuSerializer(self._get(pk)).data)

    @extend_schema(
        request=CommunicationAddonSkuWriteSerializer,
        responses={200: CommunicationAddonSkuSerializer},
    )
    def patch(self, request, pk):
        sku = self._get(pk)
        serializer = CommunicationAddonSkuWriteSerializer(
            sku, data=request.data, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        sku = serializer.save()
        return Response(CommunicationAddonSkuSerializer(sku).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        sku = self._get(pk)
        in_use = (
            sku.sms_subscriptions.exists()
            or sku.email_subscriptions.exists()
            or sku.pending_sms_subscriptions.exists()
            or sku.pending_email_subscriptions.exists()
        )
        if in_use:
            raise ValidationError({
                'detail': 'Cannot delete an addon SKU that is linked to subscriptions.',
            })
        sku.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PlatformAddonSkuSeedView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(responses={200: CommunicationAddonSkuSerializer(many=True)})
    def post(self, request):
        skus = seed_default_skus()
        return Response(CommunicationAddonSkuSerializer(skus, many=True).data)


class PlatformSchoolCreditsView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(responses={200: CreditBalancesSerializer})
    def get(self, request, pk):
        school = _school_or_404(pk)
        balances = get_balances(school)
        return Response({
            'sms': balances.get('sms', 0),
            'email': balances.get('email', 0),
            'billing_active': communications_billing_active(school),
        })


class PlatformSchoolLedgerView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]
    pagination_class = StandardResultsSetPagination

    @extend_schema(responses={200: CreditLedgerEntrySerializer(many=True)})
    def get(self, request, pk):
        school = _school_or_404(pk)
        qs = CreditLedgerEntry.objects.filter(school=school).order_by('-occurred_at')
        channel = (request.query_params.get('channel') or '').strip()
        if channel:
            qs = qs.filter(channel=channel)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(
            CreditLedgerEntrySerializer(page, many=True).data,
        )


class PlatformSchoolAddonScheduleView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(request=ScheduleAddonChangeSerializer, responses={200: SubscriptionSerializer})
    def post(self, request, pk):
        school = _school_or_404(pk)
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
            school=school,
            channel=data['channel'],
            enabled=data['enabled'],
            sku=sku,
            actor=request.platform_user,
            ip_address=client_ip(request),
        )
        subscription = (
            SchoolSubscription.objects.filter(pk=subscription.pk)
            .select_related('plan', 'pending_plan', 'sms_sku', 'email_sku', 'pending_sms_sku', 'pending_email_sku')
            .get()
        )
        return Response(SubscriptionSerializer(subscription).data)


class PlatformSchoolCreditAdjustView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(request=ManualCreditAdjustSerializer, responses={200: CreditLedgerEntrySerializer})
    def post(self, request, pk):
        school = _school_or_404(pk)
        serializer = ManualCreditAdjustSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data['delta'] == 0:
            raise ValidationError({'delta': 'Delta must be non-zero.'})
        from uuid import uuid4

        entry = manual_adjust(
            school=school,
            channel=data['channel'],
            delta=data['delta'],
            idempotency_key=f'manual:{school.pk}:{data["channel"]}:{uuid4()}',
            actor=request.platform_user,
            metadata={'reason': data.get('reason') or ''},
        )
        return Response(
            CreditLedgerEntrySerializer(entry).data,
            status=status.HTTP_201_CREATED,
        )
