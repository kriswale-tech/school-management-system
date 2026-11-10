from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.models import Invoice, Payment, Plan, SchoolSubscription, TopUpPackage
from billing.serializers import (
    CapacityUpgradeSerializer,
    ChangeIntervalSerializer,
    InvoiceSerializer,
    PaymentSerializer,
    PlanSerializer,
    PlanWriteSerializer,
    SchedulePlanChangeSerializer,
    StartSubscriptionSerializer,
    SubscriptionSerializer,
    TopUpPackageSerializer,
    TopUpPackageWriteSerializer,
)
from billing.services.capacity import active_staff_count, active_student_count
from billing.services.catalog import plan_for_usage, seed_default_plans
from billing.services.catalog_topups import seed_default_topup_packages
from billing.services.interval_change import change_billing_interval
from billing.services.subscriptions import (
    schedule_plan_change,
    start_subscription,
)
from billing.services.upgrades import apply_capacity_upgrade
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


def _plan_by_code(code: str) -> Plan:
    plan = Plan.objects.filter(code=code, is_active=True).first()
    if plan is None:
        raise ValidationError({'plan_code': 'Unknown or inactive plan.'})
    return plan


class PlatformPlanListCreateView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(responses={200: PlanSerializer(many=True)})
    def get(self, request):
        qs = Plan.objects.all().order_by('sort_order', 'student_min')
        return Response(PlanSerializer(qs, many=True).data)

    @extend_schema(request=PlanWriteSerializer, responses={201: PlanSerializer})
    def post(self, request):
        serializer = PlanWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.save()
        return Response(PlanSerializer(plan).data, status=status.HTTP_201_CREATED)


class PlatformPlanDetailView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    def _get(self, pk) -> Plan:
        plan = Plan.objects.filter(pk=pk).first()
        if plan is None:
            raise NotFound('Plan not found.')
        return plan

    @extend_schema(responses={200: PlanSerializer})
    def get(self, request, pk):
        return Response(PlanSerializer(self._get(pk)).data)

    @extend_schema(request=PlanWriteSerializer, responses={200: PlanSerializer})
    def patch(self, request, pk):
        plan = self._get(pk)
        serializer = PlanWriteSerializer(plan, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for key, value in serializer.validated_data.items():
            setattr(plan, key, value)
        plan.save()
        return Response(PlanSerializer(plan).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        from rest_framework.exceptions import ValidationError

        plan = self._get(pk)
        if plan.subscriptions.exists():
            raise ValidationError({
                'detail': 'Cannot delete a plan that is assigned to subscriptions.',
            })
        if plan.pending_subscriptions.exists():
            raise ValidationError({
                'detail': 'Cannot delete a plan that is pending on subscriptions.',
            })
        # SubscriptionPeriod / history may also PROTECT.
        if hasattr(plan, 'periods') and plan.periods.exists():
            raise ValidationError({
                'detail': 'Cannot delete a plan that appears in subscription history.',
            })
        plan.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PlatformPlanSeedView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(responses={200: PlanSerializer(many=True)})
    def post(self, request):
        plans = seed_default_plans()
        return Response(PlanSerializer(plans, many=True).data)


class PlatformSchoolSubscriptionView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(responses={200: SubscriptionSerializer})
    def get(self, request, pk):
        school = _school_or_404(pk)
        subscription = (
            SchoolSubscription.objects.filter(school=school, is_current=True)
            .select_related('plan', 'pending_plan')
            .first()
        )
        if subscription is None:
            raise NotFound('No current subscription for this school.')
        return Response(SubscriptionSerializer(subscription).data)

    @extend_schema(request=StartSubscriptionSerializer, responses={201: SubscriptionSerializer})
    def post(self, request, pk):
        school = _school_or_404(pk)
        serializer = StartSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        plan = None
        if data.get('plan_code'):
            plan = _plan_by_code(data['plan_code'])
        else:
            plan = plan_for_usage(
                students=active_student_count(school),
                staff=active_staff_count(school),
            )
        subscription = start_subscription(
            school=school,
            plan=plan,
            interval=data['interval'],
            apply_first_year_free=data['apply_first_year_free'],
            actor=request.platform_user,
            ip_address=client_ip(request),
        )
        subscription = (
            SchoolSubscription.objects.filter(pk=subscription.pk)
            .select_related('plan', 'pending_plan')
            .get()
        )
        return Response(
            SubscriptionSerializer(subscription).data,
            status=status.HTTP_201_CREATED,
        )


class PlatformSchoolScheduleChangeView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(request=SchedulePlanChangeSerializer, responses={200: SubscriptionSerializer})
    def post(self, request, pk):
        school = _school_or_404(pk)
        subscription = (
            SchoolSubscription.objects.filter(school=school, is_current=True)
            .select_related('plan', 'pending_plan')
            .first()
        )
        if subscription is None:
            raise NotFound('No current subscription for this school.')
        serializer = SchedulePlanChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = None
        plan_code = serializer.validated_data.get('plan_code')
        if plan_code:
            plan = _plan_by_code(plan_code)
        interval = serializer.validated_data.get('interval') or None
        subscription = schedule_plan_change(
            subscription=subscription,
            plan=plan,
            interval=interval,
            actor=request.platform_user,
            ip_address=client_ip(request),
        )
        subscription.refresh_from_db()
        return Response(SubscriptionSerializer(subscription).data)


class PlatformSchoolCapacityUpgradeView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(request=CapacityUpgradeSerializer, responses={200: SubscriptionSerializer})
    def post(self, request, pk):
        school = _school_or_404(pk)
        serializer = CapacityUpgradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = None
        if serializer.validated_data.get('plan_code'):
            plan = _plan_by_code(serializer.validated_data['plan_code'])
        subscription, invoice = apply_capacity_upgrade(
            school=school,
            new_plan=plan,
            actor=request.platform_user,
            ip_address=client_ip(request),
            mark_paid=serializer.validated_data.get('mark_paid', True),
        )
        subscription = (
            SchoolSubscription.objects.filter(pk=subscription.pk)
            .select_related('plan', 'pending_plan')
            .get()
        )
        return Response({
            'subscription': SubscriptionSerializer(subscription).data,
            'invoice': InvoiceSerializer(invoice).data,
        })


class PlatformSchoolInvoiceListView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]
    pagination_class = StandardResultsSetPagination

    @extend_schema(responses={200: InvoiceSerializer(many=True)})
    def get(self, request, pk):
        school = _school_or_404(pk)
        qs = (
            Invoice.objects.filter(school=school)
            .prefetch_related('lines')
            .order_by('-created_at')
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(InvoiceSerializer(page, many=True).data)


class PlatformInvoiceMarkPaidView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(responses={200: InvoiceSerializer})
    def post(self, request, pk):
        from billing.services.payments import apply_paid_invoice_effects

        invoice = Invoice.objects.filter(pk=pk).prefetch_related('lines').first()
        if invoice is None:
            raise NotFound('Invoice not found.')
        apply_paid_invoice_effects(invoice=invoice, payment=None)
        invoice = Invoice.objects.filter(pk=invoice.pk).prefetch_related('lines').get()
        return Response(InvoiceSerializer(invoice).data)


class PlatformSchoolChangeIntervalView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(request=ChangeIntervalSerializer, responses={200: SubscriptionSerializer})
    def post(self, request, pk):
        school = _school_or_404(pk)
        serializer = ChangeIntervalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription, invoice = change_billing_interval(
            school=school,
            new_interval=serializer.validated_data['interval'],
            actor=request.platform_user,
            ip_address=client_ip(request),
            mark_paid=serializer.validated_data.get('mark_paid', True),
        )
        subscription = (
            SchoolSubscription.objects.filter(pk=subscription.pk)
            .select_related('plan', 'pending_plan')
            .get()
        )
        return Response({
            'subscription': SubscriptionSerializer(subscription).data,
            'invoice': InvoiceSerializer(invoice).data,
        })


class PlatformPaymentListView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]
    pagination_class = StandardResultsSetPagination

    @extend_schema(responses={200: PaymentSerializer(many=True)})
    def get(self, request):
        qs = Payment.objects.select_related(
            'school',
            'invoice',
            'topup_purchase',
            'topup_purchase__package',
        ).order_by('-created_at')
        status_filter = (request.query_params.get('status') or '').strip()
        if status_filter:
            qs = qs.filter(status=status_filter)
        school_id = (request.query_params.get('school') or '').strip()
        if school_id:
            qs = qs.filter(school_id=school_id)
        purpose = (request.query_params.get('purpose') or '').strip()
        if purpose:
            qs = qs.filter(purpose=purpose)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(PaymentSerializer(page, many=True).data)


class PlatformSchoolPaymentListView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]
    pagination_class = StandardResultsSetPagination

    @extend_schema(responses={200: PaymentSerializer(many=True)})
    def get(self, request, pk):
        school = _school_or_404(pk)
        qs = (
            Payment.objects.filter(school=school)
            .select_related('invoice', 'topup_purchase', 'topup_purchase__package')
            .order_by('-created_at')
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(PaymentSerializer(page, many=True).data)


class PlatformTopUpPackageListCreateView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(responses={200: TopUpPackageSerializer(many=True)})
    def get(self, request):
        qs = TopUpPackage.objects.all().order_by('channel', 'sort_order', 'credits')
        return Response(TopUpPackageSerializer(qs, many=True).data)

    @extend_schema(request=TopUpPackageWriteSerializer, responses={201: TopUpPackageSerializer})
    def post(self, request):
        from billing.services.catalog_topups import apply_topup_pricing

        serializer = TopUpPackageWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        package = TopUpPackage(**serializer.validated_data)
        package.is_active = bool(serializer.validated_data.get('is_active', False))
        apply_topup_pricing(package)
        package.save()
        return Response(TopUpPackageSerializer(package).data, status=status.HTTP_201_CREATED)


class PlatformTopUpPackageDetailView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    def _get(self, pk) -> TopUpPackage:
        package = TopUpPackage.objects.filter(pk=pk).first()
        if package is None:
            raise NotFound('Top-up package not found.')
        return package

    @extend_schema(responses={200: TopUpPackageSerializer})
    def get(self, request, pk):
        return Response(TopUpPackageSerializer(self._get(pk)).data)

    @extend_schema(request=TopUpPackageWriteSerializer, responses={200: TopUpPackageSerializer})
    def patch(self, request, pk):
        from billing.services.catalog_topups import apply_topup_pricing

        package = self._get(pk)
        serializer = TopUpPackageWriteSerializer(package, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for key, value in serializer.validated_data.items():
            setattr(package, key, value)
        apply_topup_pricing(package)
        package.save()
        return Response(TopUpPackageSerializer(package).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        from rest_framework.exceptions import ValidationError

        package = self._get(pk)
        if package.purchases.exists():
            raise ValidationError({
                'detail': 'Cannot delete a top-up package that has purchase history.',
            })
        package.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PlatformTopUpPackageSeedView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(responses={200: TopUpPackageSerializer(many=True)})
    def post(self, request):
        packages = seed_default_topup_packages()
        return Response(TopUpPackageSerializer(packages, many=True).data)
