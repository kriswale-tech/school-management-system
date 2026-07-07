from rest_framework import serializers


class SetupClassStreamSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    full_name = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    is_default = serializers.BooleanField()
    is_active = serializers.BooleanField()
    capacity = serializers.IntegerField(allow_null=True)


class SetupSubjectGroupSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    is_active = serializers.BooleanField()


class SetupClassSubjectSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    class_subject_id = serializers.UUIDField()
    name = serializers.CharField()
    is_active = serializers.BooleanField()
    is_system_generated = serializers.BooleanField()
    is_editable = serializers.BooleanField()
    groups = SetupSubjectGroupSerializer(many=True)


class SetupClassLevelSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    order = serializers.IntegerField()
    is_active = serializers.BooleanField()
    is_system_generated = serializers.BooleanField()
    is_editable = serializers.BooleanField()
    streams = SetupClassStreamSerializer(many=True)
    subjects = SetupClassSubjectSerializer(many=True)


class SetupLevelSubjectSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    is_active = serializers.BooleanField()
    is_system_generated = serializers.BooleanField()
    is_editable = serializers.BooleanField()
    groups = SetupSubjectGroupSerializer(many=True)


class SetupLevelSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    order = serializers.IntegerField()
    is_active = serializers.BooleanField()
    is_system_generated = serializers.BooleanField()
    subject_scope = serializers.ChoiceField(choices=['level', 'class'])
    allows_custom_classes = serializers.BooleanField()
    classes = SetupClassLevelSerializer(many=True)
    subjects = SetupLevelSubjectSerializer(many=True)
