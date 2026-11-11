from rest_framework import serializers

from platform_admin.services import schools as school_services
from schools.models import School


class PlatformSchoolListAdminSerializer(serializers.Serializer):
    full_name = serializers.CharField(allow_blank=True)
    phone_number = serializers.CharField()
    email = serializers.CharField(allow_blank=True)


class PlatformSchoolSummarySerializer(serializers.Serializer):
    school_count = serializers.IntegerField()
    active_school_count = serializers.IntegerField()
    student_count = serializers.IntegerField()
    staff_count = serializers.IntegerField()
    overdue_school_count = serializers.IntegerField()


class PlatformSchoolListSerializer(serializers.ModelSerializer):
    """List row for platform school directory.

    ``staff_count`` = active SchoolMembership rows (admins/teachers/staff).
    ``student_count`` = active Student rows.
    ``next_renewal_at`` is the current period end for active and past-due
    subscriptions only.
    """

    staff_count = serializers.IntegerField(read_only=True)
    student_count = serializers.IntegerField(read_only=True)
    plan_name = serializers.SerializerMethodField()
    plan_code = serializers.SerializerMethodField()
    subscription_status = serializers.SerializerMethodField()
    subscription_interval = serializers.SerializerMethodField()
    next_renewal_at = serializers.SerializerMethodField()
    payment_overdue = serializers.BooleanField(read_only=True)
    admins = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = (
            'id',
            'name',
            'phone_number',
            'email',
            'region',
            'category',
            'status',
            'setup_completed',
            'staff_count',
            'student_count',
            'plan_name',
            'plan_code',
            'subscription_status',
            'subscription_interval',
            'next_renewal_at',
            'payment_overdue',
            'admins',
            'activated_at',
            'suspended_at',
            'created_at',
        )
        read_only_fields = fields

    def get_plan_name(self, school: School) -> str | None:
        subscription = school_services.current_subscription(school)
        if subscription is None:
            return None
        if subscription.plan_id:
            return subscription.plan.name
        return subscription.plan_code_snapshot or None

    def get_plan_code(self, school: School) -> str | None:
        subscription = school_services.current_subscription(school)
        if subscription is None:
            return None
        if subscription.plan_id:
            return subscription.plan.code
        return subscription.plan_code_snapshot or None

    def get_subscription_status(self, school: School) -> str | None:
        subscription = school_services.current_subscription(school)
        return subscription.status if subscription else None

    def get_subscription_interval(self, school: School) -> str | None:
        subscription = school_services.current_subscription(school)
        return subscription.interval if subscription else None

    def get_next_renewal_at(self, school: School):
        subscription = school_services.current_subscription(school)
        if subscription is None:
            return None
        if subscription.status not in school_services.RENEWING_SUBSCRIPTION_STATUSES:
            return None
        return subscription.current_period_end

    def get_admins(self, school: School) -> list[dict]:
        return [
            {
                'full_name': membership.user.get_full_name(),
                'phone_number': membership.user.phone_number,
                'email': membership.user.email or '',
            }
            for membership in school_services.directory_admins(school)
        ]


class PlatformSchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = (
            'id',
            'name',
            'address',
            'gps_address',
            'box_address',
            'phone_number',
            'phone_number_alt',
            'email',
            'motto',
            'region',
            'category',
            'status',
            'setup_completed',
            'setup_completed_at',
            'activated_at',
            'suspended_at',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'status',
            'setup_completed',
            'setup_completed_at',
            'activated_at',
            'suspended_at',
            'created_at',
            'updated_at',
        )


class PlatformSchoolCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    phone_number = serializers.RegexField(regex=r'^(\+233|0)[0-9]{9}$')
    phone_number_alt = serializers.RegexField(
        regex=r'^(\+233|0)[0-9]{9}$',
        required=False,
        allow_blank=True,
    )
    email = serializers.EmailField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True, max_length=255)
    region = serializers.CharField(required=False, allow_blank=True, max_length=100)
    category = serializers.ChoiceField(
        choices=School.Category.choices,
        required=False,
        allow_blank=True,
    )
    plan_code = serializers.SlugField(required=False, allow_blank=True)
    interval = serializers.ChoiceField(
        choices=(('monthly', 'Monthly'), ('annual', 'Annual')),
        required=False,
        allow_blank=True,
    )
    sms_sku_code = serializers.SlugField(required=False, allow_blank=True)
    email_sku_code = serializers.SlugField(required=False, allow_blank=True)

    def validate(self, attrs):
        plan_code = (attrs.get('plan_code') or '').strip()
        interval = (attrs.get('interval') or '').strip()
        if plan_code and not interval:
            raise serializers.ValidationError({
                'interval': 'Choose monthly or annual billing with a plan.',
            })
        if interval and not plan_code:
            raise serializers.ValidationError({
                'plan_code': 'Choose a plan with the billing interval.',
            })
        if (attrs.get('sms_sku_code') or attrs.get('email_sku_code')) and not plan_code:
            raise serializers.ValidationError({
                'plan_code': 'Choose a plan before adding communication add-ons.',
            })
        return attrs


class PlatformSchoolStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=School.Status.choices)
    reason = serializers.CharField(max_length=500)

    def validate_reason(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError('Enter a reason for this status change.')
        return cleaned


class PlatformSchoolAuditSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    action = serializers.CharField()
    actor_name = serializers.SerializerMethodField()
    actor_email = serializers.SerializerMethodField()
    detail = serializers.JSONField()
    created_at = serializers.DateTimeField()

    def get_actor_name(self, entry) -> str:
        actor = entry.actor
        if actor is None:
            return ''
        return actor.full_name

    def get_actor_email(self, entry) -> str:
        actor = entry.actor
        if actor is None:
            return ''
        return actor.email


class PlatformSchoolAdminSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    phone_number = serializers.CharField()
    email = serializers.CharField(allow_blank=True)
    full_name = serializers.CharField(allow_blank=True)
    role = serializers.CharField()
    is_active = serializers.BooleanField()
