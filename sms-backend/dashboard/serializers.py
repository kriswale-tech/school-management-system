from rest_framework import serializers

from activities.serializers import ActivitySerializer


class SchoolOverviewSerializer(serializers.Serializer):
    total_students = serializers.IntegerField()
    total_classes = serializers.IntegerField()
    staff_members = serializers.IntegerField()


class FeesOverviewSerializer(serializers.Serializer):
    fees_collected = serializers.DecimalField(max_digits=14, decimal_places=2)
    outstanding_balance = serializers.DecimalField(max_digits=14, decimal_places=2)
    debtors_count = serializers.IntegerField()


class AcademicOverviewSerializer(serializers.Serializer):
    reports_ready = serializers.IntegerField()
    pending_reports = serializers.IntegerField()
    released_reports = serializers.IntegerField()
    needs_correction = serializers.IntegerField()


class CoverageOverviewSerializer(serializers.Serializer):
    unassigned_classes = serializers.IntegerField()
    unassigned_subjects = serializers.IntegerField()
    empty_classes = serializers.IntegerField()


class NeedsAttentionItemSerializer(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()
    href = serializers.CharField()


class TopDebtorSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    student_code = serializers.CharField()
    full_name = serializers.CharField()
    class_display = serializers.CharField()
    outstanding_amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class AcademicProgressRowSerializer(serializers.Serializer):
    stream_id = serializers.UUIDField()
    class_level_id = serializers.UUIDField()
    level_id = serializers.UUIDField(allow_null=True)
    level_name = serializers.CharField(allow_null=True)
    display_name = serializers.CharField()
    students_count = serializers.IntegerField()
    ready_count = serializers.IntegerField()
    released_count = serializers.IntegerField()
    completed_count = serializers.IntegerField()
    ready_percent = serializers.IntegerField()
    released_percent = serializers.IntegerField()
    percent_complete = serializers.IntegerField()


class SetupHealthMetricSerializer(serializers.Serializer):
    label = serializers.CharField()
    assigned = serializers.IntegerField()
    total = serializers.IntegerField()
    percent = serializers.IntegerField()
    href = serializers.CharField()


class SetupHealthSerializer(serializers.Serializer):
    class_teachers = SetupHealthMetricSerializer()
    subject_teachers = SetupHealthMetricSerializer()
    classes_with_students = SetupHealthMetricSerializer()
    subject_groups_with_students = SetupHealthMetricSerializer()
    students_in_subject_groups = SetupHealthMetricSerializer()


class LevelOptionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class TeacherClassesOverviewSerializer(serializers.Serializer):
    classes_count = serializers.IntegerField()
    students_count = serializers.IntegerField()


class TeacherSubjectsOverviewSerializer(serializers.Serializer):
    subjects_count = serializers.IntegerField()
    students_count = serializers.IntegerField()


class TeacherAcademicOverviewSerializer(serializers.Serializer):
    pending_reports = serializers.IntegerField()
    awaiting_approval = serializers.IntegerField()
    approved_reports = serializers.IntegerField()
    subjects_to_publish = serializers.IntegerField()
    subjects_published = serializers.IntegerField()
    corrections_count = serializers.IntegerField()


class TeacherClassRowSerializer(serializers.Serializer):
    id = serializers.CharField()
    display_name = serializers.CharField()
    students_count = serializers.IntegerField()
    view_stream_id = serializers.CharField(allow_null=True)
    pending_count = serializers.IntegerField()
    awaiting_approval_count = serializers.IntegerField()
    approved_count = serializers.IntegerField()
    needs_correction_count = serializers.IntegerField()
    href = serializers.CharField()


class TeacherSubjectRowSerializer(serializers.Serializer):
    id = serializers.CharField()
    subject_name = serializers.CharField()
    display_class_name = serializers.CharField()
    subject_group_name = serializers.CharField(allow_null=True)
    students_count = serializers.IntegerField()
    published_count = serializers.IntegerField()
    is_open = serializers.BooleanField()
    needs_correction_count = serializers.IntegerField()
    href = serializers.CharField()


class TeacherDashboardSerializer(serializers.Serializer):
    is_class_teacher = serializers.BooleanField()
    is_subject_teacher = serializers.BooleanField()
    show_academic_widgets = serializers.BooleanField()
    classes_overview = TeacherClassesOverviewSerializer()
    subjects_overview = TeacherSubjectsOverviewSerializer()
    academic_overview = TeacherAcademicOverviewSerializer()
    needs_attention = NeedsAttentionItemSerializer(many=True)
    classes = TeacherClassRowSerializer(many=True)
    subjects = TeacherSubjectRowSerializer(many=True)
    activities = ActivitySerializer(many=True)


class AdminDashboardSerializer(serializers.Serializer):
    term_id = serializers.UUIDField(allow_null=True)
    term_label = serializers.CharField(allow_null=True)
    show_academic_widgets = serializers.BooleanField()
    school_overview = SchoolOverviewSerializer()
    fees_overview = FeesOverviewSerializer()
    academic_overview = AcademicOverviewSerializer()
    coverage_overview = CoverageOverviewSerializer()
    needs_attention = NeedsAttentionItemSerializer(many=True)
    top_debtors = TopDebtorSerializer(many=True)
    setup_health = SetupHealthSerializer()
    academic_progress = AcademicProgressRowSerializer(many=True)
    levels = LevelOptionSerializer(many=True)
