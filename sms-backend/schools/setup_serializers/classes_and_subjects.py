from rest_framework import serializers


class SetupClassStreamSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    full_name = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    is_default = serializers.BooleanField()
    is_active = serializers.BooleanField()
    capacity = serializers.IntegerField(allow_null=True)


class SetupClassLevelSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    order = serializers.IntegerField()
    is_active = serializers.BooleanField()
    streams = SetupClassStreamSerializer(many=True)


class SetupSubjectGroupSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    is_active = serializers.BooleanField()


class SetupLevelSubjectSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    is_active = serializers.BooleanField()
    groups = SetupSubjectGroupSerializer(many=True)


class SetupLevelSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    order = serializers.IntegerField()
    is_active = serializers.BooleanField()
    classes = SetupClassLevelSerializer(many=True)
    subjects = SetupLevelSubjectSerializer(many=True)


class ClassesAndSubjectsDataSerializer(serializers.Serializer):
    levels = SetupLevelSerializer(many=True)
