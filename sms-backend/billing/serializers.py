from rest_framework import serializers

from billing.models import (
    Invoice,
    InvoiceLine,
    Payment,
    Plan,
    PromotionCampaign,
    PromotionRedemption,
    SchoolSubscription,
    TopUpPackage,
)
from billing.services.capacity import get_capacity_snapshot, triggered_warning_levels
from billing.services.discounts import subscription_discount_summaries


class ChangeIntervalSerializer(serializers.Serializer):
    interval = serializers.ChoiceField(choices=SchoolSubscription.Interval.choices)
    mark_paid = serializers.BooleanField(required=False)


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = (
            'id',
            'code',
            'name',
            'student_min',
            'student_max',
            'staff_min',
            'staff_max',
            'price_monthly_ghs',
            'price_annual_ghs',
            'warning_thresholds',
            'sort_order',
            'is_active',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class PlanWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = (
            'code',
            'name',
            'student_min',
            'student_max',
            'staff_min',
            'staff_max',
            'price_monthly_ghs',
            'price_annual_ghs',
            'warning_thresholds',
            'sort_order',
            'is_active',
        )

    def create(self, validated_data):
        validated_data.setdefault('is_active', False)
        return super().create(validated_data)

    def validate(self, attrs):
        student_min = attrs.get(
            'student_min',
            getattr(self.instance, 'student_min', 1),
        )
        student_max = attrs.get(
            'student_max',
            getattr(self.instance, 'student_max', None),
        )
        staff_min = attrs.get(
            'staff_min',
            getattr(self.instance, 'staff_min', 1),
        )
        staff_max = attrs.get(
            'staff_max',
            getattr(self.instance, 'staff_max', None),
        )
        if student_max is not None and student_max < student_min:
            raise serializers.ValidationError({
                'student_max': 'Must be greater than or equal to student_min.',
            })
        if staff_max is not None and staff_max < staff_min:
            raise serializers.ValidationError({
                'staff_max': 'Must be greater than or equal to staff_min.',
            })
        return attrs


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = (
            'id',
            'kind',
            'description',
            'quantity',
            'unit_price_ghs',
            'amount_ghs',
            'metadata',
        )
        read_only_fields = fields


class InvoiceSerializer(serializers.ModelSerializer):
    lines = InvoiceLineSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = (
            'id',
            'school',
            'subscription',
            'currency',
            'status',
            'period_start',
            'period_end',
            'subtotal_ghs',
            'discount_ghs',
            'total_ghs',
            'amount_paid_ghs',
            'due_at',
            'paid_at',
            'notes',
            'lines',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class CapacitySerializer(serializers.Serializer):
    active_students = serializers.IntegerField()
    capacity_max = serializers.IntegerField(allow_null=True)
    active_staff = serializers.IntegerField()
    staff_capacity_max = serializers.IntegerField(allow_null=True)
    plan_code = serializers.CharField(allow_null=True)
    plan_name = serializers.CharField(allow_null=True)
    warnings = serializers.ListField(child=serializers.FloatField())
    triggered_warnings = serializers.ListField(child=serializers.FloatField())
    at_or_over_capacity = serializers.BooleanField()
    at_or_over_student_capacity = serializers.BooleanField()
    at_or_over_staff_capacity = serializers.BooleanField()
    usage_ratio = serializers.FloatField(allow_null=True)
    staff_usage_ratio = serializers.FloatField(allow_null=True)


class AddonSkuBriefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    code = serializers.CharField()
    name = serializers.CharField()
    channel = serializers.CharField()
    interval = serializers.CharField()
    credits_per_period = serializers.IntegerField()
    price_ghs = serializers.DecimalField(max_digits=12, decimal_places=2)


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    pending_plan = PlanSerializer(read_only=True)
    sms_sku = AddonSkuBriefSerializer(read_only=True)
    email_sku = AddonSkuBriefSerializer(read_only=True)
    pending_sms_sku = AddonSkuBriefSerializer(read_only=True)
    pending_email_sku = AddonSkuBriefSerializer(read_only=True)
    capacity = serializers.SerializerMethodField()
    discounts = serializers.SerializerMethodField()

    class Meta:
        model = SchoolSubscription
        fields = (
            'id',
            'school',
            'plan',
            'interval',
            'status',
            'is_current',
            'current_period_start',
            'current_period_end',
            'grace_period_ends_at',
            'dunning_notice_sent_at',
            'billing_suspended_school',
            'sms_addon_enabled',
            'email_addon_enabled',
            'sms_sku',
            'email_sku',
            'pending_plan',
            'pending_interval',
            'pending_sms_enabled',
            'pending_email_enabled',
            'pending_sms_sku',
            'pending_email_sku',
            'pending_change_effective_at',
            'plan_code_snapshot',
            'capacity_max_snapshot',
            'staff_capacity_max_snapshot',
            'app_price_snapshot_ghs',
            'capacity',
            'discounts',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

    def get_capacity(self, obj):
        snapshot = get_capacity_snapshot(obj.school)
        return {
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
        }

    def get_discounts(self, obj):
        rows = subscription_discount_summaries(obj)
        for row in rows:
            if row['starts_at'] is not None:
                row['starts_at'] = row['starts_at'].isoformat()
            if row['ends_at'] is not None:
                row['ends_at'] = row['ends_at'].isoformat()
        return rows


class StartSubscriptionSerializer(serializers.Serializer):
    plan_code = serializers.SlugField(required=False, allow_blank=True)
    interval = serializers.ChoiceField(
        choices=SchoolSubscription.Interval.choices,
        default=SchoolSubscription.Interval.ANNUAL,
    )
    apply_first_year_free = serializers.BooleanField(default=True)


class SchedulePlanChangeSerializer(serializers.Serializer):
    plan_code = serializers.SlugField(required=False, allow_blank=True)
    interval = serializers.ChoiceField(
        choices=SchoolSubscription.Interval.choices,
        required=False,
        allow_blank=True,
    )

    def validate(self, attrs):
        if not attrs.get('plan_code') and not attrs.get('interval'):
            raise serializers.ValidationError(
                'Provide a plan_code and/or interval to schedule for the next renewal.',
            )
        return attrs


class CapacityUpgradeSerializer(serializers.Serializer):
    plan_code = serializers.SlugField(required=False, allow_blank=True)
    # Platform operators may force-mark paid; school self-serve defaults unpaid.
    mark_paid = serializers.BooleanField(required=False)


class RecordTopUpSerializer(serializers.Serializer):
    package_code = serializers.SlugField()


class TopUpPackageSerializer(serializers.ModelSerializer):
    unit_price_ghs = serializers.SerializerMethodField()
    list_price_ghs = serializers.SerializerMethodField()
    provider_unit_cost_ghs = serializers.SerializerMethodField()
    cost_price_ghs = serializers.SerializerMethodField()

    class Meta:
        model = TopUpPackage
        fields = (
            'id',
            'code',
            'name',
            'channel',
            'credits',
            'discount_percent',
            'unit_price_ghs',
            'list_price_ghs',
            'provider_unit_cost_ghs',
            'cost_price_ghs',
            'price_ghs',
            'sort_order',
            'is_active',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

    def get_unit_price_ghs(self, obj):
        from communications.services.pricing import sell_unit_price_ghs

        return str(sell_unit_price_ghs(obj.channel))

    def get_list_price_ghs(self, obj):
        from communications.services.pricing import list_price_ghs

        return str(list_price_ghs(channel=obj.channel, credits=obj.credits))

    def get_provider_unit_cost_ghs(self, obj):
        from communications.services.pricing import provider_unit_cost_ghs

        return str(provider_unit_cost_ghs(obj.channel))

    def get_cost_price_ghs(self, obj):
        from communications.services.pricing import cost_price_ghs

        return str(cost_price_ghs(channel=obj.channel, credits=obj.credits))


class TopUpPackageWriteSerializer(serializers.ModelSerializer):
    """Create/update top-ups. ``price_ghs`` is computed server-side — do not send it."""

    class Meta:
        model = TopUpPackage
        fields = (
            'code',
            'name',
            'channel',
            'credits',
            'discount_percent',
            'sort_order',
            'is_active',
        )

    def create(self, validated_data):
        validated_data.setdefault('is_active', False)
        return super().create(validated_data)

    def validate_discount_percent(self, value):
        if value is None:
            return value
        if value < 0 or value > 100:
            raise serializers.ValidationError('Discount must be between 0 and 100.')
        return value

    def validate_credits(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError('Credits must be at least 1.')
        return value


class TopUpPurchaseSerializer(serializers.Serializer):
    package_code = serializers.SlugField()


class PaymentSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True)
    purpose_label = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    tag = serializers.SerializerMethodField()
    topup_channel = serializers.SerializerMethodField()
    topup_credits = serializers.SerializerMethodField()
    package_name = serializers.SerializerMethodField()
    invoice_notes = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = (
            'id',
            'school',
            'school_name',
            'invoice',
            'purpose',
            'purpose_label',
            'label',
            'tag',
            'topup_channel',
            'topup_credits',
            'package_name',
            'invoice_notes',
            'provider',
            'status',
            'amount_ghs',
            'currency',
            'reference',
            'provider_transaction_id',
            'authorization_url',
            'paid_at',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

    def get_invoice_notes(self, obj) -> str:
        if not obj.invoice_id:
            return ''
        return (getattr(obj.invoice, 'notes', None) or '').strip()

    def get_purpose_label(self, obj) -> str:
        if obj.purpose == Payment.Purpose.TOPUP:
            return 'Top-up'
        return 'Invoice'

    def get_tag(self, obj) -> str:
        if obj.purpose == Payment.Purpose.TOPUP:
            purchase = getattr(obj, 'topup_purchase', None)
            channel = (getattr(purchase, 'channel', None) or '').upper()
            return f'{channel} top-up' if channel else 'Top-up'
        return 'Invoice'

    def get_label(self, obj) -> str:
        if obj.purpose == Payment.Purpose.TOPUP:
            purchase = getattr(obj, 'topup_purchase', None)
            if purchase is not None:
                package = getattr(purchase, 'package', None)
                package_name = getattr(package, 'name', None) or 'Credit top-up'
                return f'{package_name} (+{purchase.credits} {purchase.channel.upper()})'
            return 'Credit top-up'
        notes = (getattr(obj.invoice, 'notes', None) or '').strip() if obj.invoice_id else ''
        return notes or 'Subscription invoice'

    def get_topup_channel(self, obj) -> str | None:
        if obj.purpose != Payment.Purpose.TOPUP:
            return None
        purchase = getattr(obj, 'topup_purchase', None)
        return getattr(purchase, 'channel', None)

    def get_topup_credits(self, obj) -> int | None:
        if obj.purpose != Payment.Purpose.TOPUP:
            return None
        purchase = getattr(obj, 'topup_purchase', None)
        return getattr(purchase, 'credits', None)

    def get_package_name(self, obj) -> str | None:
        if obj.purpose != Payment.Purpose.TOPUP:
            return None
        purchase = getattr(obj, 'topup_purchase', None)
        package = getattr(purchase, 'package', None) if purchase is not None else None
        return getattr(package, 'name', None)


class PaymentCheckoutSerializer(PaymentSerializer):
    """Checkout responses include the Paystack access code used to resume the modal."""

    class Meta(PaymentSerializer.Meta):
        fields = (*PaymentSerializer.Meta.fields, 'access_code')
        read_only_fields = fields


class PaymentVerifySerializer(serializers.Serializer):
    reference = serializers.CharField(max_length=100)


class UpcomingBillLineSerializer(serializers.Serializer):
    kind = serializers.CharField()
    description = serializers.CharField()
    amount_ghs = serializers.CharField()
    metadata = serializers.DictField(required=False)


class UpcomingBillSerializer(serializers.Serializer):
    kind = serializers.CharField()
    due_at = serializers.DateTimeField()
    period_start = serializers.DateTimeField()
    period_end = serializers.DateTimeField()
    plan_code = serializers.CharField()
    plan_name = serializers.CharField()
    interval = serializers.CharField()
    currency = serializers.CharField()
    subtotal_ghs = serializers.CharField()
    discount_ghs = serializers.CharField()
    total_ghs = serializers.CharField()
    discount_label = serializers.CharField(allow_null=True)
    lines = UpcomingBillLineSerializer(many=True)
    includes_pending_changes = serializers.BooleanField()
    open_invoice_id = serializers.CharField(allow_null=True)
    open_invoice_total_ghs = serializers.CharField(allow_null=True)
    open_invoice_notes = serializers.CharField(allow_blank=True)


class PaymentStatsSerializer(serializers.Serializer):
    total_paid_ghs = serializers.CharField()
    open_balance_ghs = serializers.CharField()
    successful_payments = serializers.IntegerField()
    open_invoices = serializers.IntegerField()
    paid_invoices = serializers.IntegerField()
    by_purpose = serializers.DictField(child=serializers.CharField())


class SchoolFinanceSerializer(serializers.Serializer):
    total_paid_ghs = serializers.CharField()
    outstanding_ghs = serializers.CharField()
    billed_ghs = serializers.CharField()
    discount_ghs = serializers.CharField()
    successful_payments = serializers.IntegerField()
    open_invoices = serializers.IntegerField()
    paid_invoices = serializers.IntegerField()
    invoice_count = serializers.IntegerField()
    payment_overdue = serializers.BooleanField()
    by_purpose = serializers.DictField(child=serializers.CharField())


class ExtendGraceSerializer(serializers.Serializer):
    until = serializers.DateField()

    def validate_until(self, value):
        from django.utils import timezone

        if value <= timezone.localdate():
            raise serializers.ValidationError('Choose a date after today.')
        return value


class AssignSchoolDiscountSerializer(serializers.Serializer):
    campaign_id = serializers.UUIDField()


class DiscountSchoolSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class DiscountRedemptionSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True)

    class Meta:
        model = PromotionRedemption
        fields = (
            'id',
            'school',
            'school_name',
            'subscription',
            'starts_at',
            'ends_at',
            'discount_percent',
            'applies_to',
            'schedule',
            'billing_interval',
            'revoked_at',
            'created_at',
        )
        read_only_fields = fields


class DiscountSerializer(serializers.ModelSerializer):
    schools = serializers.SerializerMethodField()
    redemption_count = serializers.SerializerMethodField()

    class Meta:
        model = PromotionCampaign
        fields = (
            'id',
            'code',
            'name',
            'discount_percent',
            'applies_to',
            'schedule',
            'audience',
            'billing_interval',
            'duration_months',
            'starts_at',
            'ends_at',
            'is_active',
            'schools',
            'redemption_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

    def get_schools(self, obj):
        return [
            {'id': str(school.id), 'name': school.name}
            for school in obj.schools.all()
        ]

    def get_redemption_count(self, obj):
        annotated = getattr(obj, 'redemption_count', None)
        if annotated is not None:
            return annotated
        return obj.redemptions.count()


class DiscountWriteSerializer(serializers.ModelSerializer):
    school_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = PromotionCampaign
        fields = (
            'code',
            'name',
            'discount_percent',
            'applies_to',
            'schedule',
            'audience',
            'billing_interval',
            'duration_months',
            'starts_at',
            'ends_at',
            'is_active',
            'school_ids',
        )

    def validate_discount_percent(self, value):
        if value <= 0 or value > 100:
            raise serializers.ValidationError('Discount must be greater than 0 and at most 100.')
        return value

    def validate_billing_interval(self, value):
        if value in (None, ''):
            return ''
        if value not in SchoolSubscription.Interval.values:
            raise serializers.ValidationError('Interval must be monthly, annual, or blank.')
        return value

    def validate(self, attrs):
        schedule = attrs.get('schedule', getattr(self.instance, 'schedule', None))
        audience = attrs.get('audience', getattr(self.instance, 'audience', None))
        starts_at = attrs.get('starts_at', getattr(self.instance, 'starts_at', None))
        ends_at = attrs.get('ends_at', getattr(self.instance, 'ends_at', None))
        duration = attrs.get('duration_months', getattr(self.instance, 'duration_months', 0))
        if schedule == PromotionCampaign.Schedule.INTRODUCTORY and (duration or 0) < 1:
            raise serializers.ValidationError({
                'duration_months': 'Enter how many months from subscription start this discount covers.',
            })
        if schedule == PromotionCampaign.Schedule.DATE_RANGE:
            if starts_at is None or ends_at is None:
                raise serializers.ValidationError({
                    'ends_at': 'A date-range discount needs a start and an end.',
                })
            if ends_at <= starts_at:
                raise serializers.ValidationError({
                    'ends_at': 'The end must be after the start. A billing month that starts at the end is full price.',
                })
        if audience == PromotionCampaign.Audience.SELECTED:
            school_ids = attrs.get('school_ids')
            existing = 0
            if self.instance is not None:
                existing = self.instance.schools.count()
            if school_ids is None and existing < 1:
                raise serializers.ValidationError({
                    'school_ids': 'Choose at least one school.',
                })
            if school_ids is not None and len(school_ids) < 1:
                raise serializers.ValidationError({
                    'school_ids': 'Choose at least one school.',
                })
        return attrs

    def _assign_schools(self, campaign, school_ids):
        if school_ids is None:
            return
        from schools.models import School

        schools = list(School.objects.filter(pk__in=school_ids))
        if len(schools) != len(set(school_ids)):
            raise serializers.ValidationError({'school_ids': 'One or more schools were not found.'})
        campaign.schools.set(schools)

    def create(self, validated_data):
        school_ids = validated_data.pop('school_ids', [])
        if validated_data.get('audience') != PromotionCampaign.Audience.SELECTED:
            school_ids = school_ids or []
        campaign = PromotionCampaign.objects.create(**validated_data)
        self._assign_schools(campaign, school_ids)
        return campaign

    def update(self, instance, validated_data):
        school_ids = validated_data.pop('school_ids', None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        self._assign_schools(instance, school_ids)
        return instance
