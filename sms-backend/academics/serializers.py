from rest_framework import serializers


class ClassEntrySerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text='Stream UUID used for enrollment.')
    class_level_id = serializers.UUIDField()
    display_name = serializers.CharField()
    student_count = serializers.IntegerField()
    is_default = serializers.BooleanField()


class AllClassesLevelSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    order = serializers.IntegerField()
    classes = ClassEntrySerializer(many=True)


class AllClassesSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    levels = AllClassesLevelSerializer(many=True)
