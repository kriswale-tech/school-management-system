from rest_framework import serializers


class NotificationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    event_type = serializers.CharField()
    title = serializers.CharField()
    body = serializers.CharField()
    href = serializers.CharField()
    target_kind = serializers.CharField()
    target_id = serializers.UUIDField(allow_null=True)
    read_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
    actor_name = serializers.SerializerMethodField()

    def get_actor_name(self, obj):
        if obj.actor_id is None:
            return ''
        return (obj.actor.get_full_name() or '').strip()


class UnreadCountSerializer(serializers.Serializer):
    count = serializers.IntegerField()


class MarkAllReadSerializer(serializers.Serializer):
    updated = serializers.IntegerField()
