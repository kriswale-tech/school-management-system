from rest_framework import serializers

from platform_admin.models import PlatformSettings


class PlatformSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSettings
        fields = (
            'id',
            'public_school_registration_enabled',
            'subscription_grace_days',
            'updated_at',
        )
        read_only_fields = ('id', 'updated_at')


class PlatformPublicConfigSerializer(serializers.Serializer):
    public_school_registration_enabled = serializers.BooleanField()
