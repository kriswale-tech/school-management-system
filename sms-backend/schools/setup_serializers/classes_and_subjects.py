from rest_framework import serializers


class SetupClassStreamSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    full_name = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    is_default = serializers.BooleanField()
    is_active = serializers.BooleanField()


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
    class_ids = serializers.ListField(child=serializers.UUIDField())
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


class CreateStreamSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=20)
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class UpdateStreamSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=20, required=False)
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    is_active = serializers.BooleanField(required=False)


class CreateSubjectGroupSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)


class UpdateSubjectGroupSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    is_active = serializers.BooleanField(required=False)


class CreateCustomClassSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    order = serializers.IntegerField(required=False, min_value=1)


class UpdateCustomClassSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    order = serializers.IntegerField(required=False, min_value=1)


class CreateSubjectSerializer(serializers.Serializer):
    level_id = serializers.UUIDField()
    name = serializers.CharField(max_length=255)
    class_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )


class UpdateSubjectSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    class_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_null=True,
    )


class AssignedClassSerializer(serializers.Serializer):
    class_id = serializers.UUIDField()
    class_name = serializers.CharField()
    class_subject_id = serializers.UUIDField()


class SubjectDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    is_active = serializers.BooleanField()
    is_system_generated = serializers.BooleanField()
    is_editable = serializers.BooleanField()
    class_ids = serializers.ListField(child=serializers.UUIDField())
    assigned_classes = AssignedClassSerializer(many=True)


class ActivationSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()


class ActivationResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    is_active = serializers.BooleanField()
