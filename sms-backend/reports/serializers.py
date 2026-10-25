from rest_framework import serializers


class TermOptionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    label = serializers.CharField()
    is_active = serializers.BooleanField()


class LevelOptionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class ClassLevelOptionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    level_id = serializers.UUIDField()


class FilterOptionsSerializer(serializers.Serializer):
    active_term_id = serializers.UUIDField(allow_null=True)
    terms = TermOptionSerializer(many=True)
    levels = LevelOptionSerializer(many=True)
    class_levels = ClassLevelOptionSerializer(many=True)


class OverviewCompareSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()
    students_count = serializers.IntegerField()
    students_with_results = serializers.IntegerField()
    published_subject_scores = serializers.IntegerField()
    average_score = serializers.FloatField(allow_null=True)
    subject_average = serializers.FloatField(allow_null=True)
    pass_rate = serializers.FloatField(allow_null=True)
    pass_mark = serializers.FloatField()
    average_score_delta = serializers.FloatField(allow_null=True)
    pass_rate_delta = serializers.FloatField(allow_null=True)


class OverviewSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()
    terms = TermOptionSerializer(many=True)
    scope_mode = serializers.CharField()
    students_count = serializers.IntegerField()
    students_with_results = serializers.IntegerField()
    published_subject_scores = serializers.IntegerField()
    average_score = serializers.FloatField(allow_null=True)
    subject_average = serializers.FloatField(allow_null=True)
    pass_rate = serializers.FloatField(allow_null=True)
    pass_mark = serializers.FloatField()
    classes_count = serializers.IntegerField()
    distinct_subjects_count = serializers.IntegerField()
    class_subjects_count = serializers.IntegerField()
    teaching_assignments_count = serializers.IntegerField()
    unassigned_class_subjects = serializers.IntegerField()
    compare = OverviewCompareSerializer(allow_null=True)


class ClassInsightRowSerializer(serializers.Serializer):
    class_level_id = serializers.UUIDField()
    stream_id = serializers.UUIDField(allow_null=True)
    display_name = serializers.CharField()
    students_count = serializers.IntegerField()
    students_with_results = serializers.IntegerField()
    published_subject_scores = serializers.IntegerField()
    average_score = serializers.FloatField(allow_null=True)
    pass_rate = serializers.FloatField(allow_null=True)


class ByClassSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()
    students_count = serializers.IntegerField()
    students_with_results = serializers.IntegerField()
    results = ClassInsightRowSerializer(many=True)


class SubjectInsightRowSerializer(serializers.Serializer):
    subject_id = serializers.UUIDField()
    subject_name = serializers.CharField()
    score_count = serializers.IntegerField()
    average_score = serializers.FloatField(allow_null=True)
    pass_rate = serializers.FloatField(allow_null=True)


class BySubjectSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()
    results = SubjectInsightRowSerializer(many=True)


class GradeDistributionRowSerializer(serializers.Serializer):
    grade = serializers.CharField()
    count = serializers.IntegerField()
    percent = serializers.FloatField()


class GradeDistributionSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()
    class_level_id = serializers.UUIDField()
    class_level_name = serializers.CharField()
    level_id = serializers.UUIDField()
    level_name = serializers.CharField()
    mode = serializers.ChoiceField(choices=['grades', 'score_bands'])
    result_type = serializers.CharField()
    pass_mark = serializers.FloatField()
    students_count = serializers.IntegerField()
    students_with_results = serializers.IntegerField()
    total_graded = serializers.IntegerField()
    results = GradeDistributionRowSerializer(many=True)


class StudentHistoryPointSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()
    average_score = serializers.FloatField()


class StudentTrendRowSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    student_id = serializers.CharField()
    class_display_name = serializers.CharField(allow_null=True)
    average_score = serializers.FloatField()
    is_passing = serializers.BooleanField()
    history = StudentHistoryPointSerializer(many=True)


class StudentTrendsSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()
    pass_mark = serializers.FloatField(required=False)
    students_count = serializers.IntegerField()
    students_with_results = serializers.IntegerField()
    below_pass_count = serializers.IntegerField()
    top_students = StudentTrendRowSerializer(many=True)
    at_risk_students = StudentTrendRowSerializer(many=True)


class HeatmapCellSerializer(serializers.Serializer):
    class_display_name = serializers.CharField()
    subject_name = serializers.CharField()
    average_score = serializers.FloatField(allow_null=True)
    score_count = serializers.IntegerField()


class HeatmapClassSizeSerializer(serializers.Serializer):
    display_name = serializers.CharField()
    students_count = serializers.IntegerField()


class SubjectHeatmapSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()
    level_id = serializers.UUIDField()
    level_name = serializers.CharField()
    students_count = serializers.IntegerField()
    classes = serializers.ListField(child=serializers.CharField())
    class_sizes = HeatmapClassSizeSerializer(many=True)
    subjects = serializers.ListField(child=serializers.CharField())
    cells = HeatmapCellSerializer(many=True)


class WorkflowRowSerializer(serializers.Serializer):
    display_name = serializers.CharField()
    class_level_id = serializers.UUIDField()
    stream_id = serializers.UUIDField()
    students_count = serializers.IntegerField()
    pending_count = serializers.IntegerField()
    ready_count = serializers.IntegerField()
    released_count = serializers.IntegerField()
    needs_correction_count = serializers.IntegerField()
    percent_complete = serializers.FloatField()
    percent_released = serializers.FloatField()


class WorkflowSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()
    pending_count = serializers.IntegerField()
    ready_count = serializers.IntegerField()
    released_count = serializers.IntegerField()
    needs_correction_count = serializers.IntegerField()
    total_students = serializers.IntegerField()
    percent_complete = serializers.FloatField(allow_null=True)
    percent_released = serializers.FloatField(allow_null=True)
    results = WorkflowRowSerializer(many=True)


class FeesRiskRowSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    student_id = serializers.CharField()
    class_display_name = serializers.CharField(allow_null=True)
    average_score = serializers.FloatField()
    outstanding_amount = serializers.FloatField()


class FeesAcademicRiskSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()
    available = serializers.BooleanField()
    pass_mark = serializers.FloatField(required=False)
    debtors_count = serializers.IntegerField()
    at_risk_count = serializers.IntegerField()
    results = FeesRiskRowSerializer(many=True)


class FinanceDebtorClassSerializer(serializers.Serializer):
    display_name = serializers.CharField()
    debtors_count = serializers.IntegerField()
    outstanding_amount = serializers.FloatField()


class FinanceTopDebtorSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    student_id = serializers.CharField()
    class_display_name = serializers.CharField()
    outstanding_amount = serializers.FloatField()


class FinanceSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()
    available = serializers.BooleanField()
    total_expected = serializers.FloatField()
    total_collected = serializers.FloatField()
    outstanding = serializers.FloatField()
    collection_rate = serializers.FloatField(allow_null=True)
    debtors_count = serializers.IntegerField()
    debtors_by_class = FinanceDebtorClassSerializer(many=True)
    top_debtors = FinanceTopDebtorSerializer(many=True)


class EnrollmentClassCountSerializer(serializers.Serializer):
    display_name = serializers.CharField()
    students_count = serializers.IntegerField()


class LeaveReasonCountSerializer(serializers.Serializer):
    reason = serializers.CharField()
    count = serializers.IntegerField()


class EnrollmentSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()
    previous_term_id = serializers.UUIDField(allow_null=True)
    previous_term_label = serializers.CharField(allow_null=True)
    enrolled_count = serializers.IntegerField()
    new_students = serializers.IntegerField()
    retained_count = serializers.IntegerField(allow_null=True)
    graduated_count = serializers.IntegerField(allow_null=True)
    left_count = serializers.IntegerField(allow_null=True)
    left_by_reason = LeaveReasonCountSerializer(many=True)
    retention_rate = serializers.FloatField(allow_null=True)
    by_class = EnrollmentClassCountSerializer(many=True)


class StaffCapacityRowSerializer(serializers.Serializer):
    teacher_id = serializers.UUIDField()
    full_name = serializers.CharField()
    is_class_teacher = serializers.BooleanField()
    is_subject_teacher = serializers.BooleanField()
    class_teacher_count = serializers.IntegerField()
    class_teacher_classes = serializers.ListField(child=serializers.CharField())
    class_teacher_students = serializers.IntegerField()
    subjects_taught_count = serializers.IntegerField()
    subject_names = serializers.ListField(child=serializers.CharField())
    teaching_assignments_count = serializers.IntegerField()
    classes_taught_count = serializers.IntegerField()
    teaching_classes = serializers.ListField(child=serializers.CharField())
    assignments = serializers.ListField(child=serializers.CharField())


class StaffCapacitySerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()
    teachers_count = serializers.IntegerField()
    class_teachers_count = serializers.IntegerField()
    subject_teachers_count = serializers.IntegerField()
    both_roles_count = serializers.IntegerField()
    classes_count = serializers.IntegerField()
    classes_without_class_teacher = serializers.IntegerField()
    average_assignments = serializers.FloatField(allow_null=True)
    results = StaffCapacityRowSerializer(many=True)


class TeacherDeskStudentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    student_id = serializers.CharField()
    average_score = serializers.FloatField()
    grade = serializers.CharField(allow_null=True)
    is_passing = serializers.BooleanField()


class TeacherDeskClassSerializer(serializers.Serializer):
    class_level_id = serializers.UUIDField()
    stream_id = serializers.UUIDField(allow_null=True)
    display_name = serializers.CharField()
    level_id = serializers.UUIDField()
    students_count = serializers.IntegerField()
    students_with_results = serializers.IntegerField()
    average_score = serializers.FloatField(allow_null=True)
    pass_rate = serializers.FloatField(allow_null=True)
    pass_mark = serializers.FloatField()
    mode = serializers.ChoiceField(choices=['grades', 'score_bands'])
    result_type = serializers.CharField()
    total_graded = serializers.IntegerField()
    grade_distribution = GradeDistributionRowSerializer(many=True)
    students = TeacherDeskStudentSerializer(many=True)


class TeacherDeskSubjectSerializer(serializers.Serializer):
    teaching_assignment_id = serializers.UUIDField()
    subject_id = serializers.UUIDField()
    subject_name = serializers.CharField()
    class_level_id = serializers.UUIDField()
    stream_id = serializers.UUIDField(allow_null=True)
    display_name = serializers.CharField()
    students_count = serializers.IntegerField()
    score_count = serializers.IntegerField()
    average_score = serializers.FloatField(allow_null=True)
    pass_rate = serializers.FloatField(allow_null=True)
    pass_mark = serializers.FloatField()
    mode = serializers.ChoiceField(choices=['grades', 'score_bands'])
    result_type = serializers.CharField()
    total_graded = serializers.IntegerField()
    grade_distribution = GradeDistributionRowSerializer(many=True)
    term_history = StudentHistoryPointSerializer(many=True)
    students = TeacherDeskStudentSerializer(many=True)


class TeacherDeskSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()
    scope_mode = serializers.CharField()
    is_class_teacher = serializers.BooleanField()
    is_subject_teacher = serializers.BooleanField()
    classes = TeacherDeskClassSerializer(many=True)
    subjects = TeacherDeskSubjectSerializer(many=True)


class ClassStreamPerformanceSerializer(TeacherDeskClassSerializer):
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()


class TeachingAssignmentPerformanceSerializer(TeacherDeskSubjectSerializer):
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()


class StudentPerformanceSubjectSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    subject_id = serializers.UUIDField(allow_null=True)
    subject_name = serializers.CharField()
    total = serializers.FloatField()
    grade = serializers.CharField(allow_null=True)
    rating = serializers.ChoiceField(
        choices=['strong', 'secure', 'borderline', 'at_risk'],
    )
    terms_with_score = serializers.IntegerField(required=False)
    terms_enrolled = serializers.IntegerField(required=False)
    incomplete = serializers.BooleanField(required=False)


class StudentPerformanceTermSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()
    class_display_name = serializers.CharField()
    overall_average = serializers.FloatField(allow_null=True)
    pass_mark = serializers.FloatField()
    mode = serializers.ChoiceField(choices=['grades', 'score_bands'])
    result_type = serializers.CharField()
    subjects = StudentPerformanceSubjectSerializer(many=True)
    total_graded = serializers.IntegerField()
    grade_distribution = GradeDistributionRowSerializer(many=True)
    expected_subjects_count = serializers.IntegerField()
    published_subjects_count = serializers.IntegerField()
    missing_subjects_count = serializers.IntegerField()
    results_incomplete = serializers.BooleanField()


class StudentSubjectTrendPointSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()
    total = serializers.FloatField()


class StudentSubjectTrendSerializer(serializers.Serializer):
    subject_name = serializers.CharField()
    points = StudentSubjectTrendPointSerializer(many=True)


class StudentPerformanceSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    full_name = serializers.CharField()
    terms = StudentPerformanceTermSerializer(many=True)
    overall_trend = StudentHistoryPointSerializer(many=True)
    subject_trends = StudentSubjectTrendSerializer(many=True)
    all_time_ranking = StudentPerformanceSubjectSerializer(many=True)
    all_time_pass_mark = serializers.FloatField()
    all_time_incomplete = serializers.BooleanField()
    enrolled_term_count = serializers.IntegerField()
