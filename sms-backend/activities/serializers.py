from rest_framework import serializers


class ActivitySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    verb = serializers.CharField()
    summary = serializers.CharField()
    href = serializers.CharField()
    actor_name = serializers.CharField()
    created_at = serializers.DateTimeField()
    target_kind = serializers.CharField()
