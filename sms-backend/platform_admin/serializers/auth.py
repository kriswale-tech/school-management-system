from rest_framework import serializers

from platform_admin.models import PlatformUser


class PlatformUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = PlatformUser
        fields = (
            'id',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'role',
            'mfa_enabled',
            'is_active',
            'created_at',
        )
        read_only_fields = fields


class PlatformLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class PlatformMfaVerifySerializer(serializers.Serializer):
    code = serializers.CharField(min_length=6, max_length=8)


class PlatformMfaSetupConfirmSerializer(serializers.Serializer):
    code = serializers.CharField(min_length=6, max_length=8)


class PlatformHelloSerializer(serializers.Serializer):
    name = serializers.CharField()
    version = serializers.CharField()
    authenticated = serializers.BooleanField()
    user = PlatformUserSerializer(allow_null=True)
