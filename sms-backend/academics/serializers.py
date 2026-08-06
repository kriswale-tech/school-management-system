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


class ClassTeacherSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()


class ClassListItemSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text='Stream UUID.')
    name = serializers.CharField(help_text='Display name, e.g. Nursery 1 A or Nursery 1.')
    level_id = serializers.UUIDField(help_text='Department (Level) UUID.')
    level_name = serializers.CharField()
    class_level_id = serializers.UUIDField()
    class_level_name = serializers.CharField()
    students_count = serializers.IntegerField()
    subjects_count = serializers.IntegerField()
    unassigned_subjects_count = serializers.IntegerField()
    class_teacher = ClassTeacherSummarySerializer(allow_null=True)
    is_default = serializers.BooleanField()
    is_assigned = serializers.BooleanField()
    needs_attention = serializers.BooleanField()
    capacity = serializers.IntegerField(allow_null=True)


class ClassListSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    results = ClassListItemSerializer(many=True)


class ClassStatsSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    total_classes = serializers.IntegerField()
    total_students = serializers.IntegerField()
    total_teachers_assigned = serializers.IntegerField()
    unassigned_classes = serializers.IntegerField()
    unassigned_class_subjects = serializers.IntegerField()
    empty_classes = serializers.IntegerField()
    classes_with_students = serializers.IntegerField()


class ClassDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text='Stream UUID.')
    name = serializers.CharField()
    level_id = serializers.UUIDField()
    level_name = serializers.CharField()
    class_level_id = serializers.UUIDField()
    class_level_name = serializers.CharField()
    students_count = serializers.IntegerField()
    subjects_count = serializers.IntegerField()
    unassigned_subjects_count = serializers.IntegerField()
    class_teacher = ClassTeacherSummarySerializer(allow_null=True)
    class_teacher_assignment_id = serializers.UUIDField(allow_null=True)
    is_default = serializers.BooleanField()
    is_assigned = serializers.BooleanField()
    needs_attention = serializers.BooleanField()
    capacity = serializers.IntegerField(allow_null=True)
    term_id = serializers.UUIDField()


class ClassStudentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    student_id = serializers.CharField()
    admission_date = serializers.DateField()


class ClassStudentListSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    results = ClassStudentSerializer(many=True)


class ClassSubjectRowSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=['class_subject', 'subject_group'])
    class_subject_id = serializers.UUIDField()
    subject_group_id = serializers.UUIDField(allow_null=True)
    name = serializers.CharField()
    subject_name = serializers.CharField()
    group_name = serializers.CharField(allow_null=True)
    students_count = serializers.IntegerField()
    teacher = ClassTeacherSummarySerializer(allow_null=True)
    teaching_assignment_id = serializers.UUIDField(allow_null=True)


class ClassSubjectListSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    results = ClassSubjectRowSerializer(many=True)


class ClassTeacherOptionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    class_teacher_summary = serializers.CharField()
    teaching_summary = serializers.CharField()


class ClassTeacherOptionListSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    results = ClassTeacherOptionSerializer(many=True)


class AssignClassTeacherSerializer(serializers.Serializer):
    teacher_id = serializers.UUIDField()


class AssignSubjectTeacherSerializer(serializers.Serializer):
    teacher_id = serializers.UUIDField()
    class_subject_id = serializers.UUIDField()
    subject_group_id = serializers.UUIDField(required=False, allow_null=True)
