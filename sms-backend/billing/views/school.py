from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from accounts.capabilities import Capability
from accounts.permissions import HasActiveSchool, HasCapability
from decimal import Decimal

from django.db.models import Sum

from billing.models import Invoice, Payment, Plan, SchoolSubscription
from billing.serializers import (
    CapacitySerializer,
    CapacityUpgradeSerializer,
    ChangeIntervalSerializer,
    InvoiceSerializer,
    PaymentSerializer,
    PaymentStatsSerializer,
    PlanSerializer,
    SchedulePlanChangeSerializer,
    SubscriptionSerializer,
    UpcomingBillSerializer,
)
from billing.services.capacity import get_capacity_snapshot, triggered_warning_levels
from billing.services.interval_change import change_billing_interval
from billing.services.invoice_hygiene import sanitize_school_invoices
from billing.services.subscriptions import schedule_plan_change
from billing.services.upcoming import build_upcoming_renewal_preview
from billing.services.upgrades import apply_capacity_upgrade
from core.pagination import StandardResultsSetPagination
from shared.views import SchoolScopedAPIView


class SchoolPlanCatalogView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.BILLING_VIEW

    @extend_schema(responses={200: PlanSerializer(many=True)})
    def get(self, request):
        qs = Plan.objects.filter(is_active=True).order_by('sort_order', 'student_min')
        return Response(PlanSerializer(qs, many=True).data)


class SchoolSubscriptionView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.BILLING_VIEW

    @extend_schema(responses={200: SubscriptionSerializer})
    def get(self, request):
        subscription = (
            SchoolSubscription.objects.filter(school=self.school, is_current=True)
            .select_related('plan', 'pending_plan')
            .first()
        )
        if subscription is None:
            raise NotFound('No current subscription.')
        return Response(SubscriptionSerializer(subscription).data)


class SchoolCapacityView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.BILLING_VIEW

    @extend_schema(responses={200: CapacitySerializer})
    def get(self, request):
        snapshot = get_capacity_snapshot(self.school)
        return Response({
            'active_students': snapshot.active_students,
            'capacity_max': snapshot.capacity_max,
            'active_staff': snapshot.active_staff,
            'staff_capacity_max': snapshot.staff_capacity_max,
            'plan_code': snapshot.plan_code,
            'plan_name': snapshot.plan_name,
            'warnings': snapshot.warnings,
            'triggered_warnings': triggered_warning_levels(snapshot),
            'at_or_over_capacity': snapshot.at_or_over_capacity,
            'at_or_over_student_capacity': snapshot.at_or_over_student_capacity,
            'at_or_over_staff_capacity': snapshot.at_or_over_staff_capacity,
            'usage_ratio': snapshot.usage_ratio,
            'staff_usage_ratio': snapshot.staff_usage_ratio,
        })


class SchoolInvoiceListView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.BILLING_VIEW
    pagination_class = StandardResultsSetPagination

    @extend_schema(responses={200: InvoiceSerializer(many=True)})
    def get(self, request):
        sanitize_school_invoices(self.school)
        qs = (
            Invoice.objects.filter(school=self.school)
            .prefetch_related('lines')
            .order_by('-created_at')
        )
        # Hide void/uncollectible clutter unless explicitly requested.
        include = (request.query_params.get('include') or '').strip().lower()
        if include != 'all':
            qs = qs.exclude(
                status__in=[Invoice.Status.VOID, Invoice.Status.UNCOLLECTIBLE, Invoice.Status.DRAFT],
            )
        status_filter = (request.query_params.get('status') or '').strip()
        if status_filter:
            qs = qs.filter(status=status_filter)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(InvoiceSerializer(page, many=True).data)


class SchoolUpcomingBillView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.BILLING_VIEW

    @extend_schema(responses={200: UpcomingBillSerializer})
    def get(self, request):
        sanitize_school_invoices(self.school)
        subscription = (
            SchoolSubscription.objects.filter(school=self.school, is_current=True)
            .select_related(
                'plan',
                'pending_plan',
                'sms_sku',
                'email_sku',
                'pending_sms_sku',
                'pending_email_sku',
            )
            .first()
        )
        if subscription is None:
            raise NotFound('No current subscription.')
        preview = build_upcoming_renewal_preview(subscription)
        return Response(UpcomingBillSerializer(preview).data)


class SchoolPaymentListView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.BILLING_VIEW
    pagination_class = StandardResultsSetPagination

    @extend_schema(responses={200: PaymentSerializer(many=True)})
    def get(self, request):
        qs = (
            Payment.objects.filter(school=self.school)
            .select_related('invoice', 'topup_purchase', 'topup_purchase__package')
            .order_by('-created_at')
        )
        status_filter = (request.query_params.get('status') or '').strip()
        if status_filter:
            qs = qs.filter(status=status_filter)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(PaymentSerializer(page, many=True).data)


class SchoolPaymentStatsView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.BILLING_VIEW

    @extend_schema(responses={200: PaymentStatsSerializer})
    def get(self, request):
        sanitize_school_invoices(self.school)
        paid_total = (
            Payment.objects.filter(
                school=self.school,
                status=Payment.Status.SUCCESS,
            ).aggregate(total=Sum('amount_ghs'))['total']
            or Decimal('0.00')
        )
        open_balance = (
            Invoice.objects.filter(
                school=self.school,
                status=Invoice.Status.OPEN,
            ).aggregate(total=Sum('total_ghs'))['total']
            or Decimal('0.00')
        )
        by_purpose = {}
        for row in (
            Payment.objects.filter(school=self.school, status=Payment.Status.SUCCESS)
            .values('purpose')
            .annotate(total=Sum('amount_ghs'))
        ):
            by_purpose[row['purpose']] = str(row['total'] or Decimal('0.00'))
        payload = {
            'total_paid_ghs': str(paid_total),
            'open_balance_ghs': str(open_balance),
            'successful_payments': Payment.objects.filter(
                school=self.school,
                status=Payment.Status.SUCCESS,
            ).count(),
            'open_invoices': Invoice.objects.filter(
                school=self.school,
                status=Invoice.Status.OPEN,
            ).count(),
            'paid_invoices': Invoice.objects.filter(
                school=self.school,
                status=Invoice.Status.PAID,
            ).count(),
            'by_purpose': by_purpose,
        }
        return Response(PaymentStatsSerializer(payload).data)


class SchoolSchedulePlanChangeView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.BILLING_MANAGE

    @extend_schema(request=SchedulePlanChangeSerializer, responses={200: SubscriptionSerializer})
    def post(self, request):
        subscription = (
            SchoolSubscription.objects.filter(school=self.school, is_current=True)
            .select_related('plan', 'pending_plan')
            .first()
        )
        if subscription is None:
            raise NotFound('No current subscription.')
        serializer = SchedulePlanChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = None
        plan_code = serializer.validated_data.get('plan_code')
        if plan_code:
            plan = Plan.objects.filter(code=plan_code, is_active=True).first()
            if plan is None:
                raise ValidationError({'plan_code': 'Unknown or inactive plan.'})
        interval = serializer.validated_data.get('interval') or None
        subscription = schedule_plan_change(
            subscription=subscription,
            plan=plan,
            interval=interval,
            actor=None,
            ip_address=None,
        )
        subscription.refresh_from_db()
        return Response(SubscriptionSerializer(subscription).data)


class SchoolCapacityUpgradeView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.BILLING_MANAGE

    @extend_schema(request=CapacityUpgradeSerializer, responses={200: SubscriptionSerializer})
    def post(self, request):
        serializer = CapacityUpgradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = None
        if serializer.validated_data.get('plan_code'):
            plan = Plan.objects.filter(
                code=serializer.validated_data['plan_code'],
                is_active=True,
            ).first()
            if plan is None:
                raise ValidationError({'plan_code': 'Unknown or inactive plan.'})
        # School self-serve leaves invoices open for Paystack checkout unless
        # the client explicitly requests complimentary/manual mark_paid.
        subscription, invoice = apply_capacity_upgrade(
            school=self.school,
            new_plan=plan,
            actor=None,
            mark_paid=serializer.validated_data.get('mark_paid', False),
        )
        subscription = (
            SchoolSubscription.objects.filter(pk=subscription.pk)
            .select_related('plan', 'pending_plan')
            .get()
        )
        return Response(
            {
                'subscription': SubscriptionSerializer(subscription).data,
                'invoice': InvoiceSerializer(invoice).data,
            },
            status=status.HTTP_200_OK,
        )


class SchoolChangeIntervalView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, HasCapability]
    required_capability = Capability.BILLING_MANAGE

    @extend_schema(request=ChangeIntervalSerializer, responses={200: SubscriptionSerializer})
    def post(self, request):
        serializer = ChangeIntervalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription, invoice = change_billing_interval(
            school=self.school,
            new_interval=serializer.validated_data['interval'],
            actor=None,
            mark_paid=serializer.validated_data.get('mark_paid', False),
        )
        subscription = (
            SchoolSubscription.objects.filter(pk=subscription.pk)
            .select_related('plan', 'pending_plan')
            .get()
        )
        return Response(
            {
                'subscription': SubscriptionSerializer(subscription).data,
                'invoice': InvoiceSerializer(invoice).data,
            },
            status=status.HTTP_200_OK,
        )
