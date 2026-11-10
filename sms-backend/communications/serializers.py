from rest_framework import serializers

from billing.models import Plan
from communications.models import CommunicationAddonSku, CreditLedgerEntry


class AddonPlanBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ('id', 'code', 'name', 'is_active')
        read_only_fields = fields


class CommunicationAddonSkuSerializer(serializers.ModelSerializer):
    """Fixed ``price_ghs`` is what renewals charge; reference fields are informational."""

    unit_price_ghs = serializers.SerializerMethodField()
    reference_price_ghs = serializers.SerializerMethodField()
    provider_unit_cost_ghs = serializers.SerializerMethodField()
    cost_price_ghs = serializers.SerializerMethodField()
    available_plans = AddonPlanBriefSerializer(many=True, read_only=True)
    available_plan_ids = serializers.SerializerMethodField()

    class Meta:
        model = CommunicationAddonSku
        fields = (
            'id',
            'code',
            'name',
            'channel',
            'interval',
            'credits_per_period',
            'price_ghs',
            'unit_price_ghs',
            'reference_price_ghs',
            'provider_unit_cost_ghs',
            'cost_price_ghs',
            'available_plans',
            'available_plan_ids',
            'sort_order',
            'is_active',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

    def get_available_plan_ids(self, obj):
        return [str(pk) for pk in obj.available_plans.values_list('pk', flat=True)]

    def get_unit_price_ghs(self, obj):
        from communications.services.pricing import sell_unit_price_ghs

        return str(sell_unit_price_ghs(obj.channel))

    def get_reference_price_ghs(self, obj):
        from communications.services.pricing import list_price_ghs

        return str(
            list_price_ghs(channel=obj.channel, credits=obj.credits_per_period),
        )

    def get_provider_unit_cost_ghs(self, obj):
        from communications.services.pricing import provider_unit_cost_ghs

        return str(provider_unit_cost_ghs(obj.channel))

    def get_cost_price_ghs(self, obj):
        from communications.services.pricing import cost_price_ghs

        return str(
            cost_price_ghs(channel=obj.channel, credits=obj.credits_per_period),
        )


class CommunicationAddonSkuWriteSerializer(serializers.ModelSerializer):
    available_plan_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Plan.objects.all(),
        source='available_plans',
        required=False,
    )

    class Meta:
        model = CommunicationAddonSku
        fields = (
            'code',
            'name',
            'channel',
            'interval',
            'credits_per_period',
            'price_ghs',
            'available_plan_ids',
            'sort_order',
            'is_active',
        )

    def validate_credits_per_period(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError('Credits must be at least 1.')
        return value

    def validate_price_ghs(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('Price cannot be negative.')
        return value

    def create(self, validated_data):
        plans = validated_data.pop('available_plans', [])
        # New catalog rows stay off until explicitly activated.
        validated_data.setdefault('is_active', False)
        sku = CommunicationAddonSku.objects.create(**validated_data)
        if plans is not None:
            sku.available_plans.set(plans)
        return sku

    def update(self, instance, validated_data):
        plans = validated_data.pop('available_plans', None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if plans is not None:
            instance.available_plans.set(plans)
        return instance


class CreditBalancesSerializer(serializers.Serializer):
    sms = serializers.IntegerField()
    email = serializers.IntegerField()
    billing_active = serializers.BooleanField()


class CreditLedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditLedgerEntry
        fields = (
            'id',
            'channel',
            'entry_type',
            'delta',
            'balance_after',
            'idempotency_key',
            'occurred_at',
            'metadata',
            'created_at',
        )
        read_only_fields = fields


class ScheduleAddonChangeSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=['sms', 'email'])
    enabled = serializers.BooleanField()
    sku_code = serializers.SlugField(required=False, allow_blank=True)


class ManualCreditAdjustSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=['sms', 'email'])
    delta = serializers.IntegerField()
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)
