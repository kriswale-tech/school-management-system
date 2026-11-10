"""Platform Admin Messages API views (v4.1 §2.16–§2.17)."""

from __future__ import annotations

from datetime import datetime, time

from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from communications.models import (
    MessagingAllowancePolicy,
    Provider,
    ProviderAccount,
    ProviderBalanceSnapshot,
    ProviderExpense,
    ProviderPurchase,
    ProviderReconciliationItem,
    ProviderReconciliationRun,
    ResendUsageSnapshot,
    SmsEncodingConfig,
)
from communications.serializers_messages import (
    EmailPricingConfigCreateSerializer,
    EmailPricingConfigSerializer,
    MessagingAllowancePolicySerializer,
    MessagingAllowancePolicyWriteSerializer,
    ProviderBalanceSnapshotSerializer,
    ProviderExpenseCreateSerializer,
    ProviderExpenseSerializer,
    ProviderPurchaseCreateSerializer,
    ProviderPurchaseSerializer,
    ReconcileRequestSerializer,
    ReconciliationItemSerializer,
    ReconciliationRunSerializer,
    ResendUsageSnapshotSerializer,
    ResolveReconciliationItemSerializer,
    SmsCalculatorSerializer,
    SmsEncodingConfigCreateSerializer,
    SmsEncodingConfigSerializer,
)
from communications.services.aggregates import classification_breakdown
from communications.services.analytics import school_report, school_usage_matrix
from communications.services.exports import build_export
from communications.services.overview import messaging_overview
from communications.services.pricing import (
    create_email_config_version,
    create_sms_config_version,
    email_config_history,
    get_active_email_config,
    get_active_sms_configs,
    invalidate_sms_limit_cache,
    sms_config_history,
)
from communications.services.profitability import messaging_profitability
from communications.services.providers import (
    ensure_provider_accounts,
    latest_arkesel_snapshot,
    latest_ses_snapshot,
    sync_arkesel_balance,
    sync_ses_usage,
)
from communications.services.ranges import resolve_range
from communications.services.reconciliation import reconcile_arkesel, reconcile_ses, resolve_item
from communications.services.segments import analyze_sms
from communications.services.transactions import transaction_feed
from core.pagination import StandardResultsSetPagination
from platform_admin.authentication import PlatformJWTCookieAuthentication
from platform_admin.models import PlatformUser
from platform_admin.permissions import HasPlatformRole, IsPlatformAuthenticated
from platform_admin.services.audit import record_audit
from platform_admin.utils import client_ip
from schools.models import School

# Role shortcuts
SA = PlatformUser.Role.SUPER_ADMIN
FIN = PlatformUser.Role.FINANCE
OPS = PlatformUser.Role.OPERATIONS
SUP = PlatformUser.Role.SUPPORT

READ_ROLES = [SA, FIN, OPS, SUP]
FINANCE_WRITE = [SA, FIN]
OPS_WRITE = [SA, OPS]
OPS_SYNC = [SA, OPS]
RECON_RESOLVE = [SA, FIN, OPS]
PROFIT_ROLES = [SA, FIN, OPS]


class MessagesAPIView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated, HasPlatformRole]
    allowed_roles = READ_ROLES
    pagination_class = StandardResultsSetPagination

    def paginate(self, queryset, serializer_class):
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, self.request, view=self)
        return paginator.get_paginated_response(serializer_class(page, many=True).data)

    def require_roles(self, roles):
        user = self.request.platform_user
        if user.role not in roles and user.role != SA:
            raise PermissionDenied('You do not have permission to perform this action.')


def _school_or_none(request):
    raw = (request.query_params.get('school') or '').strip()
    if not raw:
        return None
    school = School.objects.filter(pk=raw).first()
    if school is None:
        raise ValidationError({'school': 'School not found.'})
    return school


def _school_or_404(pk) -> School:
    school = School.objects.filter(pk=pk).first()
    if school is None:
        raise NotFound('School not found.')
    return school


def _range(request):
    return resolve_range(request.query_params)


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

class MessagesOverviewView(MessagesAPIView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        school = _school_or_none(request)
        channel = (request.query_params.get('channel') or '').strip() or None
        classification = (request.query_params.get('classification') or '').strip() or None
        return Response(
            messaging_overview(
                date_range=_range(request),
                school=school,
                channel=channel,
                classification=classification,
            ),
        )


# ---------------------------------------------------------------------------
# SMS / email pricing
# ---------------------------------------------------------------------------

class SmsEncodingListCreateView(MessagesAPIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            self.allowed_roles = FINANCE_WRITE
        else:
            self.allowed_roles = READ_ROLES
        return super().get_permissions()

    @extend_schema(responses={200: SmsEncodingConfigSerializer(many=True)})
    def get(self, request):
        configs = list(get_active_sms_configs().values())
        if not configs:
            configs = list(SmsEncodingConfig.objects.filter(is_active=True))
        return Response(SmsEncodingConfigSerializer(configs, many=True).data)

    @extend_schema(request=SmsEncodingConfigCreateSerializer, responses={201: SmsEncodingConfigSerializer})
    def post(self, request):
        ser = SmsEncodingConfigCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        config = create_sms_config_version(
            encoding=data['encoding'],
            provider_cost_per_segment_ghs=data.get('provider_cost_per_segment_ghs'),
            school_price_per_segment_ghs=data.get('school_price_per_segment_ghs'),
            single_segment_limit=data.get('single_segment_limit'),
            multipart_segment_limit=data.get('multipart_segment_limit'),
            notes=data.get('notes', ''),
            actor=request.platform_user,
            ip_address=client_ip(request),
        )
        invalidate_sms_limit_cache()
        return Response(SmsEncodingConfigSerializer(config).data, status=status.HTTP_201_CREATED)


class SmsEncodingHistoryView(MessagesAPIView):
    @extend_schema(responses={200: SmsEncodingConfigSerializer(many=True)})
    def get(self, request):
        encoding = (request.query_params.get('encoding') or '').strip() or None
        return Response(SmsEncodingConfigSerializer(sms_config_history(encoding), many=True).data)


class SmsEncodingVersionView(MessagesAPIView):
    allowed_roles = FINANCE_WRITE

    @extend_schema(request=SmsEncodingConfigCreateSerializer, responses={201: SmsEncodingConfigSerializer})
    def patch(self, request, pk):
        previous = SmsEncodingConfig.objects.filter(pk=pk).first()
        if previous is None:
            raise NotFound('SMS encoding config not found.')
        ser = SmsEncodingConfigCreateSerializer(data={**request.data, 'encoding': previous.encoding})
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        config = create_sms_config_version(
            encoding=previous.encoding,
            provider_cost_per_segment_ghs=data.get('provider_cost_per_segment_ghs'),
            school_price_per_segment_ghs=data.get('school_price_per_segment_ghs'),
            single_segment_limit=data.get('single_segment_limit'),
            multipart_segment_limit=data.get('multipart_segment_limit'),
            notes=data.get('notes', ''),
            actor=request.platform_user,
            ip_address=client_ip(request),
        )
        invalidate_sms_limit_cache()
        return Response(SmsEncodingConfigSerializer(config).data, status=status.HTTP_201_CREATED)


class EmailPricingListCreateView(MessagesAPIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            self.allowed_roles = FINANCE_WRITE
        else:
            self.allowed_roles = READ_ROLES
        return super().get_permissions()

    @extend_schema(responses={200: EmailPricingConfigSerializer})
    def get(self, request):
        config = get_active_email_config()
        if config is None:
            return Response(None)
        return Response(EmailPricingConfigSerializer(config).data)

    @extend_schema(request=EmailPricingConfigCreateSerializer, responses={201: EmailPricingConfigSerializer})
    def post(self, request):
        ser = EmailPricingConfigCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        config = create_email_config_version(
            school_price_per_credit_ghs=data.get('school_price_per_credit_ghs'),
            estimated_provider_cost_per_email_ghs=data.get('estimated_provider_cost_per_email_ghs'),
            notes=data.get('notes', ''),
            actor=request.platform_user,
            ip_address=client_ip(request),
        )
        return Response(EmailPricingConfigSerializer(config).data, status=status.HTTP_201_CREATED)


class EmailPricingHistoryView(MessagesAPIView):
    @extend_schema(responses={200: EmailPricingConfigSerializer(many=True)})
    def get(self, request):
        return Response(EmailPricingConfigSerializer(email_config_history(), many=True).data)


class SmsCalculatorView(MessagesAPIView):
    @extend_schema(request=SmsCalculatorSerializer, responses={200: dict})
    def post(self, request):
        ser = SmsCalculatorSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(analyze_sms(ser.validated_data.get('body') or ''))


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

class ProviderAccountListView(MessagesAPIView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        accounts = ensure_provider_accounts()
        arkesel = latest_arkesel_snapshot()
        ses = latest_ses_snapshot()
        return Response([
            {
                'id': str(account.pk),
                'provider': account.provider,
                'channel': account.channel,
                'display_name': account.display_name,
                'api_status': account.api_status,
                'last_synced_at': account.last_synced_at,
                'last_error': account.last_error,
                'last_webhook_at': account.last_webhook_at,
                'webhook_signature_failures': account.webhook_signature_failures,
                'is_active': account.is_active,
                'latest_balance': (
                    ProviderBalanceSnapshotSerializer(arkesel).data
                    if account.provider == Provider.ARKESEL and arkesel
                    else None
                ),
                'latest_usage': (
                    ResendUsageSnapshotSerializer(ses).data
                    if account.provider == Provider.SES and ses
                    else None
                ),
            }
            for account in accounts
        ])


class ArkeselSyncBalanceView(MessagesAPIView):
    allowed_roles = OPS_SYNC

    def post(self, request):
        result = sync_arkesel_balance(actor=request.platform_user)
        snapshot = result.get('snapshot') if isinstance(result, dict) else result
        if snapshot is None and isinstance(result, dict):
            raise ValidationError(result.get('error') or 'Arkesel sync failed.')
        return Response(ProviderBalanceSnapshotSerializer(snapshot).data)


class ArkeselSnapshotListView(MessagesAPIView):
    def get(self, request):
        account = ProviderAccount.objects.filter(
            provider=Provider.ARKESEL, channel='sms',
        ).first()
        qs = ProviderBalanceSnapshot.objects.none()
        if account:
            qs = ProviderBalanceSnapshot.objects.filter(provider_account=account).order_by('-captured_at')
        return self.paginate(qs, ProviderBalanceSnapshotSerializer)


class SesSyncUsageView(MessagesAPIView):
    allowed_roles = OPS_SYNC

    def post(self, request):
        result = sync_ses_usage(actor=request.platform_user)
        snapshot = result.get('snapshot') if isinstance(result, dict) else result
        if snapshot is None and isinstance(result, dict):
            raise ValidationError(result.get('error') or 'SES sync failed.')
        data = ResendUsageSnapshotSerializer(snapshot).data
        data['placeholder'] = bool(result.get('placeholder'))
        return Response(data)


# Legacy aliases — same handlers, old paths.
ResendSyncUsageView = SesSyncUsageView


class SesUsageListView(MessagesAPIView):
    def get(self, request):
        account = ProviderAccount.objects.filter(
            provider=Provider.SES, channel='email',
        ).first()
        qs = ResendUsageSnapshot.objects.none()
        if account:
            qs = ResendUsageSnapshot.objects.filter(provider_account=account).order_by('-captured_at')
        return self.paginate(qs, ResendUsageSnapshotSerializer)


ResendUsageListView = SesUsageListView


# ---------------------------------------------------------------------------
# Purchases / expenses
# ---------------------------------------------------------------------------

class PurchaseListCreateView(MessagesAPIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            self.allowed_roles = FINANCE_WRITE
        else:
            self.allowed_roles = [SA, FIN, OPS]
        return super().get_permissions()

    def get(self, request):
        qs = ProviderPurchase.objects.select_related('recorded_by').order_by('-purchased_at')
        provider = (request.query_params.get('provider') or '').strip()
        if provider:
            qs = qs.filter(provider=provider)
        return self.paginate(qs, ProviderPurchaseSerializer)

    def post(self, request):
        ser = ProviderPurchaseCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        purchase = ProviderPurchase(
            provider=data['provider'],
            channel=data['channel'],
            amount_ghs=data['amount_ghs'],
            credits_or_units=data['credits_or_units'],
            provider_reference=data.get('provider_reference', ''),
            purchased_at=data['purchased_at'],
            payment_method=data.get('payment_method', ''),
            notes=data.get('notes', ''),
            recorded_by=request.platform_user,
        )
        purchase.recompute_effective_cost()
        purchase.save()
        record_audit(
            actor=request.platform_user,
            action='messages.provider_purchase.created',
            target_type='provider_purchase',
            target_id=str(purchase.pk),
            detail={
                'provider': purchase.provider,
                'amount_ghs': str(purchase.amount_ghs),
                'credits_or_units': purchase.credits_or_units,
            },
            ip_address=client_ip(request),
        )
        return Response(ProviderPurchaseSerializer(purchase).data, status=status.HTTP_201_CREATED)


class ExpenseListCreateView(MessagesAPIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            self.allowed_roles = FINANCE_WRITE
        else:
            self.allowed_roles = [SA, FIN, OPS]
        return super().get_permissions()

    def get(self, request):
        qs = ProviderExpense.objects.select_related('recorded_by').order_by('-period_start')
        provider = (request.query_params.get('provider') or '').strip()
        if provider:
            qs = qs.filter(provider=provider)
        return self.paginate(qs, ProviderExpenseSerializer)

    def post(self, request):
        ser = ProviderExpenseCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        start = data['period_start']
        end = data['period_end']
        if not isinstance(start, datetime):
            start = timezone.make_aware(datetime.combine(start, time.min))
        if not isinstance(end, datetime):
            end = timezone.make_aware(datetime.combine(end, time.max))
        expense = ProviderExpense.objects.create(
            provider=data['provider'],
            channel=data['channel'],
            expense_kind=data['expense_kind'],
            period_start=start,
            period_end=end,
            amount_ghs=data['amount_ghs'],
            units=data.get('units'),
            notes=data.get('notes', ''),
            source=ProviderExpense.Source.MANUAL,
            recorded_by=request.platform_user,
        )
        record_audit(
            actor=request.platform_user,
            action='messages.provider_expense.created',
            target_type='provider_expense',
            target_id=str(expense.pk),
            detail={
                'provider': expense.provider,
                'expense_kind': expense.expense_kind,
                'amount_ghs': str(expense.amount_ghs),
            },
            ip_address=client_ip(request),
        )
        return Response(ProviderExpenseSerializer(expense).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Schools
# ---------------------------------------------------------------------------

class SchoolUsageView(MessagesAPIView):
    def get(self, request):
        rows = school_usage_matrix(
            date_range=_range(request),
            channel=(request.query_params.get('channel') or '').strip() or None,
            classification=(request.query_params.get('classification') or '').strip() or None,
            search=(request.query_params.get('q') or '').strip(),
        )
        # Manual pagination over list payload
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(rows, request, view=self)
        return paginator.get_paginated_response(page)


class SchoolReportView(MessagesAPIView):
    def get(self, request, pk):
        school = _school_or_404(pk)
        return Response(
            school_report(
                school=school,
                date_range=_range(request),
                channel=(request.query_params.get('channel') or '').strip() or None,
            ),
        )


# ---------------------------------------------------------------------------
# Allowances / free usage
# ---------------------------------------------------------------------------

class AllowanceListCreateView(MessagesAPIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            self.allowed_roles = OPS_WRITE
        else:
            self.allowed_roles = READ_ROLES
        return super().get_permissions()

    def get(self, request):
        qs = MessagingAllowancePolicy.objects.select_related('school', 'created_by').order_by('-starts_at')
        school = (request.query_params.get('school') or '').strip()
        channel = (request.query_params.get('channel') or '').strip()
        if school:
            qs = qs.filter(school_id=school)
        if channel:
            qs = qs.filter(channel=channel)
        return Response(MessagingAllowancePolicySerializer(qs, many=True).data)

    def post(self, request):
        ser = MessagingAllowancePolicyWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        school = None
        if data.get('school'):
            school = School.objects.get(pk=data['school'])
        policy = MessagingAllowancePolicy.objects.create(
            name=data['name'],
            scope=data['scope'],
            school=school,
            channel=data['channel'],
            classification=data['classification'],
            monthly_free_units=data['monthly_free_units'],
            daily_limit_units=data.get('daily_limit_units'),
            applies_to_events=data.get('applies_to_events') or [],
            budget_ghs=data.get('budget_ghs'),
            alert_thresholds=data.get('alert_thresholds') or [],
            exhausted_behavior=data['exhausted_behavior'],
            starts_at=data['starts_at'],
            ends_at=data.get('ends_at'),
            is_active=data.get('is_active', True),
            notes=data.get('notes', ''),
            created_by=request.platform_user,
        )
        record_audit(
            actor=request.platform_user,
            action='messages.allowance.created',
            target_type='messaging_allowance_policy',
            target_id=str(policy.pk),
            detail={'name': policy.name, 'channel': policy.channel, 'scope': policy.scope},
            ip_address=client_ip(request),
        )
        return Response(
            MessagingAllowancePolicySerializer(policy).data,
            status=status.HTTP_201_CREATED,
        )


class AllowanceDetailView(MessagesAPIView):
    allowed_roles = OPS_WRITE

    def patch(self, request, pk):
        policy = MessagingAllowancePolicy.objects.filter(pk=pk).first()
        if policy is None:
            raise NotFound('Allowance policy not found.')
        ser = MessagingAllowancePolicyWriteSerializer(instance=policy, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        for field, value in data.items():
            if field == 'school':
                policy.school = School.objects.filter(pk=value).first() if value else None
            else:
                setattr(policy, field, value)
        policy.save()
        record_audit(
            actor=request.platform_user,
            action='messages.allowance.updated',
            target_type='messaging_allowance_policy',
            target_id=str(policy.pk),
            detail=dict(data),
            ip_address=client_ip(request),
        )
        return Response(MessagingAllowancePolicySerializer(policy).data)


class FreeUsageView(MessagesAPIView):
    def get(self, request):
        date_range = _range(request)
        school = _school_or_none(request)
        sms = classification_breakdown(
            start=date_range.start, end=date_range.end, channel='sms', school=school,
        )
        email = classification_breakdown(
            start=date_range.start, end=date_range.end, channel='email', school=school,
        )
        return Response({
            'range': date_range.as_dict(),
            'sms': sms,
            'email': email,
        })


# ---------------------------------------------------------------------------
# Profitability / transactions / exports
# ---------------------------------------------------------------------------

class ProfitabilityView(MessagesAPIView):
    allowed_roles = PROFIT_ROLES

    def get(self, request):
        view = (request.query_params.get('view') or 'usage').strip()
        channel = (request.query_params.get('channel') or '').strip() or None
        return Response(
            messaging_profitability(
                date_range=_range(request),
                view=view,
                channel=channel,
                school=_school_or_none(request),
            ),
        )


class TransactionsView(MessagesAPIView):
    allowed_roles = [SA, FIN, OPS, SUP]

    def get(self, request):
        date_range = _range(request)
        type_raw = (request.query_params.get('type') or '').strip()
        rows = transaction_feed(
            date_range=date_range,
            types=[type_raw] if type_raw else None,
            provider=(request.query_params.get('provider') or '').strip(),
            school_id=(request.query_params.get('school') or '').strip() or None,
            channel=(request.query_params.get('channel') or '').strip(),
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(rows, request, view=self)
        return paginator.get_paginated_response(page)


class ExportView(MessagesAPIView):
    allowed_roles = [SA, FIN, OPS]

    def get(self, request):
        if request.platform_user.role == OPS and request.query_params.get('type') in {
            'profitability', 'provider_purchases', 'provider_expenses',
        }:
            # Ops may export operational datasets; finance owns money exports.
            if request.query_params.get('type') == 'profitability':
                raise PermissionDenied('Finance role required for profitability exports.')
        export_type = (request.query_params.get('type') or '').strip()
        fmt = (request.query_params.get('format') or 'csv').strip().lower()
        payload = build_export(
            export_type=export_type,
            fmt=fmt,
            date_range=_range(request),
            params=request.query_params,
        )
        record_audit(
            actor=request.platform_user,
            action='messages.export.generated',
            target_type='messages_export',
            target_id=export_type,
            detail={'format': fmt, 'filename': payload['filename']},
            ip_address=client_ip(request),
        )
        response = HttpResponse(payload['body'], content_type=payload['content_type'])
        response['Content-Disposition'] = f'attachment; filename="{payload["filename"]}"'
        return response


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------

class ReconcileProviderView(MessagesAPIView):
    allowed_roles = OPS_SYNC

    def post(self, request, provider):
        provider = (provider or '').strip().lower()
        ser = ReconcileRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        date_range = _range(request)
        window_start = data.get('window_start') or date_range.start
        window_end = data.get('window_end') or date_range.end
        if provider == Provider.ARKESEL:
            run = reconcile_arkesel(
                window_start=window_start,
                window_end=window_end,
                actor=request.platform_user,
            )
        elif provider in {Provider.SES, Provider.RESEND, 'ses', 'resend'}:
            run = reconcile_ses(
                window_start=window_start,
                window_end=window_end,
                actor=request.platform_user,
            )
        else:
            raise ValidationError({'provider': 'Supported providers: arkesel, ses.'})
        return Response(ReconciliationRunSerializer(run).data, status=status.HTTP_201_CREATED)


class ReconciliationRunListView(MessagesAPIView):
    allowed_roles = READ_ROLES

    def get(self, request):
        qs = ProviderReconciliationRun.objects.select_related('triggered_by').order_by('-started_at')
        provider = (request.query_params.get('provider') or '').strip()
        if provider:
            qs = qs.filter(provider=provider)
        return self.paginate(qs, ReconciliationRunSerializer)


class ReconciliationItemListView(MessagesAPIView):
    allowed_roles = READ_ROLES

    def get(self, request, run_id):
        run = ProviderReconciliationRun.objects.filter(pk=run_id).first()
        if run is None:
            raise NotFound('Reconciliation run not found.')
        qs = ProviderReconciliationItem.objects.filter(run=run).select_related(
            'school', 'resolved_by',
        ).order_by('-created_at')
        resolution = (request.query_params.get('resolution') or '').strip()
        if resolution:
            qs = qs.filter(resolution=resolution)
        return self.paginate(qs, ReconciliationItemSerializer)


class ReconciliationItemResolveView(MessagesAPIView):
    allowed_roles = RECON_RESOLVE

    def post(self, request, run_id, item_id):
        item = ProviderReconciliationItem.objects.filter(pk=item_id, run_id=run_id).first()
        if item is None:
            raise NotFound('Reconciliation item not found.')
        ser = ResolveReconciliationItemSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        item = resolve_item(
            item=item,
            resolution=data['resolution'],
            note=data.get('resolution_note', ''),
            actor=request.platform_user,
            ip_address=client_ip(request),
        )
        return Response(ReconciliationItemSerializer(item).data)
