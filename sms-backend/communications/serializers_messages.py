"""Serializers for Platform Admin Messages APIs (v4.1)."""

from __future__ import annotations

from rest_framework import serializers

from communications.models import (
    EmailPricingConfig,
    MessagingAllowancePolicy,
    ProviderBalanceSnapshot,
    ProviderExpense,
    ProviderPurchase,
    ProviderReconciliationItem,
    ProviderReconciliationRun,
    ResendUsageSnapshot,
    SmsEncodingConfig,
)
from schools.models import School


class SmsEncodingConfigSerializer(serializers.ModelSerializer):
    changed_by_email = serializers.SerializerMethodField()

    class Meta:
        model = SmsEncodingConfig
        fields = (
            'id',
            'encoding',
            'provider_cost_per_segment_ghs',
            'school_price_per_segment_ghs',
            'single_segment_limit',
            'multipart_segment_limit',
            'effective_from',
            'effective_to',
            'is_active',
            'changed_by',
            'changed_by_email',
            'notes',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'effective_from',
            'effective_to',
            'is_active',
            'changed_by',
            'changed_by_email',
            'created_at',
            'updated_at',
        )

    def get_changed_by_email(self, obj):
        return getattr(obj.changed_by, 'email', None)


class SmsEncodingConfigCreateSerializer(serializers.Serializer):
    encoding = serializers.ChoiceField(choices=SmsEncodingConfig.Encoding.choices)
    provider_cost_per_segment_ghs = serializers.DecimalField(
        max_digits=12, decimal_places=6, required=False,
    )
    school_price_per_segment_ghs = serializers.DecimalField(
        max_digits=12, decimal_places=6, required=False,
    )
    single_segment_limit = serializers.IntegerField(min_value=1, required=False)
    multipart_segment_limit = serializers.IntegerField(min_value=1, required=False)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=255)


class EmailPricingConfigSerializer(serializers.ModelSerializer):
    changed_by_email = serializers.SerializerMethodField()
    provider_cost_is_estimated = serializers.SerializerMethodField()

    class Meta:
        model = EmailPricingConfig
        fields = (
            'id',
            'school_price_per_credit_ghs',
            'estimated_provider_cost_per_email_ghs',
            'billing_unit',
            'provider_cost_is_estimated',
            'effective_from',
            'effective_to',
            'is_active',
            'changed_by',
            'changed_by_email',
            'notes',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

    def get_changed_by_email(self, obj):
        return getattr(obj.changed_by, 'email', None)

    def get_provider_cost_is_estimated(self, obj):
        return True


class EmailPricingConfigCreateSerializer(serializers.Serializer):
    school_price_per_credit_ghs = serializers.DecimalField(
        max_digits=12, decimal_places=6, required=False,
    )
    estimated_provider_cost_per_email_ghs = serializers.DecimalField(
        max_digits=12, decimal_places=6, required=False,
    )
    notes = serializers.CharField(required=False, allow_blank=True, max_length=255)


class SmsCalculatorSerializer(serializers.Serializer):
    body = serializers.CharField(allow_blank=True, required=False, default='')


class ProviderPurchaseSerializer(serializers.ModelSerializer):
    recorded_by_email = serializers.SerializerMethodField()

    class Meta:
        model = ProviderPurchase
        fields = (
            'id',
            'provider',
            'channel',
            'amount_ghs',
            'credits_or_units',
            'effective_cost_per_unit',
            'provider_reference',
            'purchased_at',
            'payment_method',
            'notes',
            'recorded_by',
            'recorded_by_email',
            'created_at',
        )
        read_only_fields = (
            'id',
            'effective_cost_per_unit',
            'recorded_by',
            'recorded_by_email',
            'created_at',
        )

    def get_recorded_by_email(self, obj):
        return getattr(obj.recorded_by, 'email', None)


class ProviderPurchaseCreateSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=['arkesel', 'ses', 'resend'], default='arkesel')
    channel = serializers.ChoiceField(choices=['sms', 'email'], default='sms')
    amount_ghs = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    credits_or_units = serializers.IntegerField(min_value=1)
    provider_reference = serializers.CharField(required=False, allow_blank=True, max_length=120)
    purchased_at = serializers.DateTimeField()
    payment_method = serializers.CharField(required=False, allow_blank=True, max_length=60)
    notes = serializers.CharField(required=False, allow_blank=True)


class ProviderExpenseSerializer(serializers.ModelSerializer):
    recorded_by_email = serializers.SerializerMethodField()

    class Meta:
        model = ProviderExpense
        fields = (
            'id',
            'provider',
            'channel',
            'expense_kind',
            'period_start',
            'period_end',
            'amount_ghs',
            'units',
            'notes',
            'source',
            'recorded_by',
            'recorded_by_email',
            'created_at',
        )
        read_only_fields = (
            'id',
            'source',
            'recorded_by',
            'recorded_by_email',
            'created_at',
        )

    def get_recorded_by_email(self, obj):
        return getattr(obj.recorded_by, 'email', None)


class ProviderExpenseCreateSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=['arkesel', 'ses', 'resend'], default='ses')
    channel = serializers.ChoiceField(choices=['sms', 'email'], default='email')
    expense_kind = serializers.ChoiceField(choices=ProviderExpense.ExpenseKind.choices)
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    amount_ghs = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    units = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    notes = serializers.CharField(required=False, allow_blank=True)


class ProviderBalanceSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderBalanceSnapshot
        fields = (
            'id',
            'sms_balance',
            'main_balance_text',
            'captured_at',
            'source',
            'created_at',
        )


class ResendUsageSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResendUsageSnapshot
        fields = (
            'id',
            'monthly_used',
            'monthly_limit',
            'daily_used',
            'daily_limit',
            'sent_count',
            'received_count',
            'captured_at',
            'source',
            'created_at',
        )


class MessagingAllowancePolicySerializer(serializers.ModelSerializer):
    school_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    created_by_email = serializers.SerializerMethodField()

    class Meta:
        model = MessagingAllowancePolicy
        fields = (
            'id',
            'name',
            'scope',
            'school',
            'school_name',
            'channel',
            'classification',
            'monthly_free_units',
            'daily_limit_units',
            'applies_to_events',
            'budget_ghs',
            'alert_thresholds',
            'exhausted_behavior',
            'starts_at',
            'ends_at',
            'is_active',
            'notes',
            'created_by',
            'created_by_email',
            'status',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'created_by',
            'created_by_email',
            'school_name',
            'status',
            'created_at',
            'updated_at',
        )

    def get_school_name(self, obj):
        return obj.school.name if obj.school_id else None

    def get_created_by_email(self, obj):
        return getattr(obj.created_by, 'email', None)

    def get_status(self, obj):
        from communications.services.allowances import allowance_status

        return allowance_status(obj)


class MessagingAllowancePolicyWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    scope = serializers.ChoiceField(choices=MessagingAllowancePolicy.Scope.choices)
    school = serializers.UUIDField(required=False, allow_null=True)
    channel = serializers.ChoiceField(choices=MessagingAllowancePolicy.Channel.choices)
    classification = serializers.ChoiceField(
        choices=MessagingAllowancePolicy.Classification.choices,
        default=MessagingAllowancePolicy.Classification.FREE,
    )
    monthly_free_units = serializers.IntegerField(min_value=0, default=0)
    daily_limit_units = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    applies_to_events = serializers.ListField(
        child=serializers.CharField(max_length=40),
        required=False,
        default=list,
    )
    budget_ghs = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True,
    )
    alert_thresholds = serializers.ListField(
        child=serializers.FloatField(min_value=0, max_value=1),
        required=False,
        default=list,
    )
    exhausted_behavior = serializers.ChoiceField(
        choices=MessagingAllowancePolicy.ExhaustedBehavior.choices,
        default=MessagingAllowancePolicy.ExhaustedBehavior.FALLBACK_PAID,
    )
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField(required=False, allow_null=True)
    is_active = serializers.BooleanField(default=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        scope = attrs.get('scope') or getattr(self.instance, 'scope', None)
        school = attrs.get('school', serializers.empty)
        if school is serializers.empty and self.instance is not None:
            school = self.instance.school_id
        if scope == MessagingAllowancePolicy.Scope.PLATFORM and school:
            raise serializers.ValidationError({'school': 'Platform-scoped policies cannot bind a school.'})
        if scope == MessagingAllowancePolicy.Scope.SCHOOL and not school:
            raise serializers.ValidationError({'school': 'School-scoped policies require a school.'})
        if school and scope == MessagingAllowancePolicy.Scope.SCHOOL:
            if not School.objects.filter(pk=school).exists():
                raise serializers.ValidationError({'school': 'School not found.'})
        return attrs


class ReconciliationRunSerializer(serializers.ModelSerializer):
    triggered_by_email = serializers.SerializerMethodField()

    class Meta:
        model = ProviderReconciliationRun
        fields = (
            'id',
            'provider',
            'channel',
            'window_start',
            'window_end',
            'status',
            'matched_count',
            'unmatched_count',
            'discrepancy_count',
            'checked_count',
            'started_at',
            'finished_at',
            'error_detail',
            'triggered_by',
            'triggered_by_email',
            'created_at',
        )

    def get_triggered_by_email(self, obj):
        return getattr(obj.triggered_by, 'email', None)


class ReconciliationItemSerializer(serializers.ModelSerializer):
    school_name = serializers.SerializerMethodField()
    resolved_by_email = serializers.SerializerMethodField()

    class Meta:
        model = ProviderReconciliationItem
        fields = (
            'id',
            'run',
            'provider',
            'channel',
            'school',
            'school_name',
            'internal_delivery_type',
            'internal_delivery_id',
            'provider_message_id',
            'discrepancy_type',
            'internal_value',
            'provider_value',
            'detail',
            'resolution',
            'resolution_note',
            'resolved_by',
            'resolved_by_email',
            'resolved_at',
            'created_at',
        )

    def get_school_name(self, obj):
        return obj.school.name if obj.school_id else None

    def get_resolved_by_email(self, obj):
        return getattr(obj.resolved_by, 'email', None)


class ResolveReconciliationItemSerializer(serializers.Serializer):
    resolution = serializers.ChoiceField(
        choices=['accepted', 'adjusted', 'ignored'],
    )
    resolution_note = serializers.CharField(allow_blank=True, required=False, default='')


class ReconcileRequestSerializer(serializers.Serializer):
    window_start = serializers.DateTimeField(required=False)
    window_end = serializers.DateTimeField(required=False)
