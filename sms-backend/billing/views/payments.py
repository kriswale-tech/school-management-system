import json

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.capabilities import Capability
from accounts.permissions import HasActiveSchool, HasCapability
from billing.models import Invoice, TopUpPackage
from billing.serializers import (
    InvoiceSerializer,
    PaymentSerializer,
    PaymentVerifySerializer,
    TopUpPackageSerializer,
    TopUpPurchaseSerializer,
)
from billing.services.payments import (
    handle_paystack_webhook_event,
    start_invoice_checkout,
    start_topup_checkout,
    verify_and_fulfill,
)
from billing.services.paystack import verify_webhook_signature
from shared.views import SchoolScopedAPIView


class SchoolTopUpPackageListView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.BILLING_VIEW

    @extend_schema(responses={200: TopUpPackageSerializer(many=True)})
    def get(self, request):
        qs = TopUpPackage.objects.filter(is_active=True).order_by('channel', 'sort_order')
        channel = (request.query_params.get('channel') or '').strip().lower()
        if channel in {TopUpPackage.Channel.SMS, TopUpPackage.Channel.EMAIL}:
            qs = qs.filter(channel=channel)
        return Response(TopUpPackageSerializer(qs, many=True).data)


class SchoolInvoicePayView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.BILLING_MANAGE

    @extend_schema(responses={200: PaymentSerializer})
    def post(self, request, pk):
        invoice = Invoice.objects.filter(pk=pk, school=self.school).first()
        if invoice is None:
            raise NotFound('Invoice not found.')
        payment = start_invoice_checkout(
            school=self.school,
            invoice=invoice,
            actor_user=request.user,
        )
        return Response(PaymentSerializer(payment).data)


class SchoolTopUpPurchaseView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.BILLING_MANAGE

    @extend_schema(request=TopUpPurchaseSerializer, responses={200: PaymentSerializer})
    def post(self, request):
        serializer = TopUpPurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        package = TopUpPackage.objects.filter(
            code=serializer.validated_data['package_code'],
            is_active=True,
        ).first()
        if package is None:
            raise ValidationError({'package_code': 'Unknown or inactive package.'})
        payment = start_topup_checkout(
            school=self.school,
            package=package,
            actor_user=request.user,
        )
        return Response(PaymentSerializer(payment).data)


class SchoolPaymentVerifyView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.BILLING_MANAGE

    @extend_schema(request=PaymentVerifySerializer, responses={200: PaymentSerializer})
    def post(self, request):
        serializer = PaymentVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = verify_and_fulfill(reference=serializer.validated_data['reference'])
        if payment.school_id != self.school.pk:
            raise NotFound('Payment not found.')
        payload = {
            'payment': PaymentSerializer(payment).data,
        }
        if payment.invoice_id:
            invoice = Invoice.objects.prefetch_related('lines').get(pk=payment.invoice_id)
            payload['invoice'] = InvoiceSerializer(invoice).data
        return Response(payload)


@method_decorator(csrf_exempt, name='dispatch')
class PaystackSaaSWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        signature = request.headers.get('x-paystack-signature') or request.META.get(
            'HTTP_X_PAYSTACK_SIGNATURE',
            '',
        )
        raw_body = request.body
        if not verify_webhook_signature(body=raw_body, signature=signature):
            return Response({'detail': 'Invalid signature.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            event = json.loads(raw_body.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return Response({'detail': 'Invalid JSON.'}, status=status.HTTP_400_BAD_REQUEST)

        payment = handle_paystack_webhook_event(event)
        return Response({
            'received': True,
            'reference': payment.reference if payment else None,
            'status': payment.status if payment else None,
        })
