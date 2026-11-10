from rest_framework import serializers

from platform_admin.models import SchoolAdminInvite


class SchoolAdminInviteSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True)
    accept_url = serializers.SerializerMethodField()

    class Meta:
        model = SchoolAdminInvite
        fields = (
            'id',
            'school',
            'school_name',
            'phone_number',
            'email',
            'first_name',
            'last_name',
            'status',
            'expires_at',
            'accepted_at',
            'created_at',
            'accept_url',
        )
        read_only_fields = fields

    def get_accept_url(self, obj):
        from platform_admin.services.invites import invite_accept_url

        if obj.status != SchoolAdminInvite.Status.PENDING:
            return ''
        return invite_accept_url(obj.token)


class SchoolAdminInviteCreateSerializer(serializers.Serializer):
    phone_number = serializers.RegexField(regex=r'^(\+233|0)[0-9]{9}$')
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)


class SchoolAdminInvitePreviewSerializer(serializers.Serializer):
    school_name = serializers.CharField()
    phone_number = serializers.CharField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    status = serializers.CharField()
    expires_at = serializers.DateTimeField()
    school_status = serializers.CharField()


class SchoolAdminInviteAcceptResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    school_id = serializers.UUIDField()
    school_name = serializers.CharField()
    phone_number = serializers.CharField()
    created_user = serializers.BooleanField()
