from rest_framework import serializers


class SetupTeacherProfileSerializer(serializers.Serializer):
    profile_picture = serializers.URLField(allow_null=True)
    bio = serializers.CharField(allow_null=True)
    date_of_birth = serializers.DateField(allow_null=True)
    gender = serializers.CharField(allow_null=True)
    address = serializers.CharField(allow_null=True)
    phone_number_alt = serializers.CharField(allow_null=True)


class SetupClassTeacherAssignmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    class_level_id = serializers.UUIDField()
    class_level_name = serializers.CharField()
    stream_id = serializers.UUIDField(allow_null=True)
    stream_name = serializers.CharField(allow_null=True)


class SetupTeachingAssignmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    class_subject_id = serializers.UUIDField()
    class_level_id = serializers.UUIDField()
    class_level_name = serializers.CharField()
    subject_id = serializers.UUIDField()
    subject_name = serializers.CharField()
    stream_id = serializers.UUIDField(allow_null=True)
    stream_name = serializers.CharField(allow_null=True)
    subject_group_id = serializers.UUIDField(allow_null=True)
    subject_group_name = serializers.CharField(allow_null=True)


class SetupTeacherSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone_number = serializers.CharField()
    email = serializers.EmailField()
    role = serializers.CharField()
    is_active = serializers.BooleanField()
    profile = SetupTeacherProfileSerializer(allow_null=True)
    class_teacher_assignments = SetupClassTeacherAssignmentSerializer(many=True)
    teaching_assignments = SetupTeachingAssignmentSerializer(many=True)


class CreateClassTeacherAssignmentSerializer(serializers.Serializer):
    teacher_id = serializers.UUIDField()
    class_level_id = serializers.UUIDField()
    stream_id = serializers.UUIDField(required=False, allow_null=True)


class CreateTeachingAssignmentSerializer(serializers.Serializer):
    teacher_id = serializers.UUIDField()
    class_subject_id = serializers.UUIDField()
    stream_id = serializers.UUIDField(required=False, allow_null=True)
    subject_group_id = serializers.UUIDField(required=False, allow_null=True)
