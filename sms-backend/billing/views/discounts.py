from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.models import PromotionCampaign, PromotionRedemption
from billing.serializers import (
    DiscountRedemptionSerializer,
    DiscountSerializer,
    DiscountWriteSerializer,
)
from platform_admin.authentication import PlatformJWTCookieAuthentication
from platform_admin.permissions import IsPlatformAuthenticated
from platform_admin.services.audit import record_audit
from platform_admin.utils import client_ip


def _campaign_or_404(pk) -> PromotionCampaign:
    campaign = (
        PromotionCampaign.objects.filter(pk=pk)
        .prefetch_related('schools')
        .annotate(redemption_count=Count('redemptions'))
        .first()
    )
    if campaign is None:
        raise NotFound('Discount not found.')
    return campaign


class PlatformDiscountListCreateView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(responses={200: DiscountSerializer(many=True)})
    def get(self, request):
        qs = (
            PromotionCampaign.objects.all()
            .prefetch_related('schools')
            .annotate(redemption_count=Count('redemptions'))
        )
        return Response(DiscountSerializer(qs, many=True).data)

    @extend_schema(request=DiscountWriteSerializer, responses={201: DiscountSerializer})
    def post(self, request):
        serializer = DiscountWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            campaign = serializer.save()
        record_audit(
            actor=request.platform_user,
            action='billing.discount.created',
            target_type='promotion_campaign',
            target_id=str(campaign.pk),
            detail={'code': campaign.code, 'name': campaign.name},
            ip_address=client_ip(request),
        )
        campaign = _campaign_or_404(campaign.pk)
        return Response(DiscountSerializer(campaign).data, status=status.HTTP_201_CREATED)


class PlatformDiscountDetailView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(responses={200: DiscountSerializer})
    def get(self, request, pk):
        campaign = _campaign_or_404(pk)
        payload = DiscountSerializer(campaign).data
        redemptions = (
            campaign.redemptions.select_related('school')
            .order_by('-created_at')
        )
        payload['redemptions'] = DiscountRedemptionSerializer(redemptions, many=True).data
        return Response(payload)

    @extend_schema(request=DiscountWriteSerializer, responses={200: DiscountSerializer})
    def patch(self, request, pk):
        campaign = _campaign_or_404(pk)
        serializer = DiscountWriteSerializer(campaign, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            campaign = serializer.save()
        record_audit(
            actor=request.platform_user,
            action='billing.discount.updated',
            target_type='promotion_campaign',
            target_id=str(campaign.pk),
            detail={'code': campaign.code},
            ip_address=client_ip(request),
        )
        campaign = _campaign_or_404(campaign.pk)
        return Response(DiscountSerializer(campaign).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        campaign = _campaign_or_404(pk)
        if campaign.redemptions.exists():
            raise ValidationError({
                'detail': 'This discount has already been applied to a school. Deactivate it instead.',
            })
        code = campaign.code
        campaign.delete()
        record_audit(
            actor=request.platform_user,
            action='billing.discount.deleted',
            target_type='promotion_campaign',
            target_id=str(pk),
            detail={'code': code},
            ip_address=client_ip(request),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class PlatformDiscountRevokeView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(responses={200: DiscountRedemptionSerializer})
    def post(self, request, pk, redemption_id):
        redemption = (
            PromotionRedemption.objects.filter(pk=redemption_id, campaign_id=pk)
            .select_related('school', 'campaign')
            .first()
        )
        if redemption is None:
            raise NotFound('Discount assignment not found.')
        if redemption.revoked_at is None:
            redemption.revoked_at = timezone.now()
            redemption.save(update_fields=['revoked_at', 'updated_at'])
            record_audit(
                actor=request.platform_user,
                action='billing.discount.revoked',
                target_type='school',
                target_id=str(redemption.school_id),
                detail={
                    'campaign_code': redemption.campaign.code,
                    'redemption_id': str(redemption.pk),
                },
                ip_address=client_ip(request),
            )
        return Response(DiscountRedemptionSerializer(redemption).data)


class PlatformDiscountRestoreView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(responses={200: DiscountRedemptionSerializer})
    def post(self, request, pk, redemption_id):
        redemption = (
            PromotionRedemption.objects.filter(pk=redemption_id, campaign_id=pk)
            .select_related('school', 'campaign')
            .first()
        )
        if redemption is None:
            raise NotFound('Discount assignment not found.')
        if redemption.revoked_at is not None:
            redemption.revoked_at = None
            redemption.save(update_fields=['revoked_at', 'updated_at'])
            record_audit(
                actor=request.platform_user,
                action='billing.discount.restored',
                target_type='school',
                target_id=str(redemption.school_id),
                detail={
                    'campaign_code': redemption.campaign.code,
                    'redemption_id': str(redemption.pk),
                },
                ip_address=client_ip(request),
            )
        return Response(DiscountRedemptionSerializer(redemption).data)
