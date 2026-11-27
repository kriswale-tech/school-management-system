from uuid import UUID

from rest_framework import serializers

from schools.models import School


class PlatformAuditLogSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    action = serializers.CharField()
    actor_name = serializers.SerializerMethodField()
    actor_email = serializers.SerializerMethodField()
    target_type = serializers.CharField()
    target_id = serializers.CharField()
    target_label = serializers.SerializerMethodField()
    detail = serializers.JSONField()
    ip_address = serializers.IPAddressField(allow_null=True)
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

    def get_target_label(self, entry) -> str:
        if entry.target_type != 'school' or not entry.target_id:
            return ''
        schools = self.context.get('schools') or {}
        try:
            key = UUID(str(entry.target_id))
        except ValueError:
            return ''
        school = schools.get(key)
        return school.name if school else ''


def schools_for_entries(entries) -> dict:
    ids = []
    for entry in entries:
        if entry.target_type != 'school' or not entry.target_id:
            continue
        try:
            ids.append(UUID(str(entry.target_id)))
        except ValueError:
            continue
    if not ids:
        return {}
    return School.objects.in_bulk(ids)
