from rest_framework import serializers

from notifications.models import GuardianDelivery


class MessagingOverviewSerializer(serializers.Serializer):
    period = serializers.CharField()
    period_start = serializers.CharField()
    period_end = serializers.CharField()
    credits = serializers.DictField()
    usage = serializers.DictField()
    usage_7d = serializers.DictField()
    open_failures = serializers.IntegerField()


class GuardianDeliverySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    student_name = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    status_description = serializers.SerializerMethodField()
    can_resend = serializers.SerializerMethodField()
    display_error = serializers.SerializerMethodField()

    STATUS_LABELS = {
        GuardianDelivery.Status.QUEUED: 'Queued',
        GuardianDelivery.Status.PROCESSING: 'Processing',
        GuardianDelivery.Status.SUBMITTED: 'Submitted',
        GuardianDelivery.Status.DELIVERED: 'Delivered',
        GuardianDelivery.Status.FAILED: 'Failed',
        GuardianDelivery.Status.UNKNOWN: 'Unknown',
        GuardianDelivery.Status.SKIPPED: 'Skipped',
        GuardianDelivery.Status.SENT: 'Submitted',
    }
    STATUS_DESCRIPTIONS = {
        GuardianDelivery.Status.QUEUED: 'Waiting to be sent.',
        GuardianDelivery.Status.PROCESSING: 'Being submitted to the SMS provider.',
        GuardianDelivery.Status.SUBMITTED: 'The SMS provider accepted the request.',
        GuardianDelivery.Status.DELIVERED: 'Successfully delivered.',
        GuardianDelivery.Status.FAILED: 'Confirmed unsuccessful.',
        GuardianDelivery.Status.UNKNOWN: 'Submission status could not be confirmed.',
        GuardianDelivery.Status.SKIPPED: 'Not sent.',
        GuardianDelivery.Status.SENT: 'The SMS provider accepted the request.',
    }

    class Meta:
        model = GuardianDelivery
        fields = (
            'id',
            'event_type',
            'channel',
            'status',
            'status_label',
            'status_description',
            'recipient_address',
            'body_preview',
            'provider_message_id',
            'provider_status',
            'skip_reason',
            'error_message',
            'user_error_message',
            'display_error',
            'segments',
            'credits_charged',
            'can_resend',
            'source_delivery',
            'idempotency_key',
            'parent',
            'parent_name',
            'student',
            'student_name',
            'status_updated_at',
            'created_at',
        )
        read_only_fields = fields

    def get_student_name(self, obj) -> str | None:
        student = obj.student
        if student is None:
            return None
        parts = [student.first_name, student.other_names, student.last_name]
        return ' '.join(part for part in parts if part).strip() or None

    def get_status_label(self, obj) -> str:
        return self.STATUS_LABELS.get(obj.status, obj.status.replace('_', ' ').title())

    def get_status_description(self, obj) -> str:
        return self.STATUS_DESCRIPTIONS.get(obj.status, '')

    def get_display_error(self, obj) -> str:
        return (obj.user_error_message or obj.error_message or obj.skip_reason or '').strip()

    def get_can_resend(self, obj) -> bool:
        body = (obj.body_text or obj.body_preview or '').strip()
        if not body:
            return False
        return obj.status in (
            GuardianDelivery.Status.FAILED,
            GuardianDelivery.Status.SKIPPED,
        )


class EligibleDeliveryItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    channel = serializers.CharField()
    segments = serializers.IntegerField()


class EligibleResendSelectionSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    limit = serializers.IntegerField()
    capped = serializers.BooleanField()
    ids = serializers.ListField(child=serializers.UUIDField())
    items = EligibleDeliveryItemSerializer(many=True)
    sms_credits = serializers.IntegerField()
    email_credits = serializers.IntegerField()


class BulkRetryDeliverySerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False, max_length=100)


class BulkRetryResultSerializer(serializers.Serializer):
    queued = serializers.IntegerField()
    skipped = serializers.ListField(child=serializers.DictField())


class RetryDeliverySerializer(serializers.Serializer):
    queued = serializers.IntegerField()
    channel = serializers.CharField()
    idempotency_key = serializers.CharField()
    source_delivery_id = serializers.UUIDField()


class VerifyDeliverySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    can_resend = serializers.BooleanField()
    provider_status = serializers.CharField(allow_blank=True)
    verified = serializers.BooleanField()


class PlaceholderSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()


class MessageTemplateSerializer(serializers.Serializer):
    event_type = serializers.CharField()
    label = serializers.CharField()
    placeholders = PlaceholderSerializer(many=True)
    sms_prefix_example = serializers.CharField()
    sms_body = serializers.CharField(allow_blank=True)
    sms_body_is_custom = serializers.BooleanField()
    sms_body_default = serializers.CharField()
    sms_body_all_time = serializers.CharField(allow_blank=True)
    sms_body_all_time_is_custom = serializers.BooleanField()
    sms_body_all_time_default = serializers.CharField(allow_blank=True)
    email_subject = serializers.CharField(allow_blank=True)
    email_subject_is_custom = serializers.BooleanField()
    email_subject_default = serializers.CharField()
    email_text = serializers.CharField(allow_blank=True)
    email_text_is_custom = serializers.BooleanField()
    email_text_default = serializers.CharField()
    email_html = serializers.CharField(allow_blank=True)
    email_html_is_custom = serializers.BooleanField()
    updated_at = serializers.CharField(allow_null=True)


class MessageTemplateUpdateSerializer(serializers.Serializer):
    event_type = serializers.CharField()
    sms_body = serializers.CharField(required=False, allow_blank=True)
    sms_body_all_time = serializers.CharField(required=False, allow_blank=True)
    email_subject = serializers.CharField(required=False, allow_blank=True)
    email_text = serializers.CharField(required=False, allow_blank=True)
    email_html = serializers.CharField(required=False, allow_blank=True)
    restore = serializers.ListField(
        child=serializers.ChoiceField(
            choices=[
                'sms_body',
                'sms_body_all_time',
                'email_subject',
                'email_text',
                'email_html',
            ],
        ),
        required=False,
    )


class MessageTemplatePreviewSerializer(serializers.Serializer):
    event_type = serializers.CharField()
    channel = serializers.ChoiceField(choices=['sms', 'email'])
    sms_body = serializers.CharField(required=False, allow_blank=True)
    sms_body_all_time = serializers.CharField(required=False, allow_blank=True)
    email_subject = serializers.CharField(required=False, allow_blank=True)
    email_text = serializers.CharField(required=False, allow_blank=True)
    all_time = serializers.BooleanField(required=False, default=False)
