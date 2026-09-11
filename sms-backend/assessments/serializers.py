from decimal import Decimal

from rest_framework import serializers


class CaItemSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=100)
    max_marks = serializers.DecimalField(
        max_digits=7,
        decimal_places=2,
        min_value=Decimal('0.01'),
    )
    order = serializers.IntegerField(read_only=True)


class CaItemWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    max_marks = serializers.DecimalField(
        max_digits=7,
        decimal_places=2,
        min_value=Decimal('0.01'),
    )


class WorkspaceStudentMarkSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    ca = serializers.DictField(
        child=serializers.DecimalField(max_digits=7, decimal_places=2),
    )
    exam = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=Decimal('0'),
        max_value=Decimal('100'),
    )


class SaveMarksSerializer(serializers.Serializer):
    students = WorkspaceStudentMarkSerializer(many=True)


class AssessmentWeightsSerializer(serializers.Serializer):
    continuous_assessment_weight = serializers.FloatField()
    exam_weight = serializers.FloatField()


class GradeBandPayloadSerializer(serializers.Serializer):
    grade = serializers.CharField()
    min_score = serializers.IntegerField()
    max_score = serializers.IntegerField()
    remark = serializers.CharField()
    order = serializers.IntegerField()


class WorkspaceStudentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    student_id = serializers.CharField()
    admission_date = serializers.DateField()
    ca = serializers.DictField(child=serializers.FloatField(allow_null=True))
    exam = serializers.FloatField(allow_null=True)
    class_score = serializers.FloatField(allow_null=True)
    exam_contribution = serializers.FloatField(allow_null=True)
    total = serializers.FloatField(allow_null=True)
    grade = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    is_published = serializers.BooleanField()


class AssessmentWorkspaceSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    weights = AssessmentWeightsSerializer()
    grade_bands = GradeBandPayloadSerializer(many=True)
    result_type = serializers.CharField()
    uses_grades = serializers.BooleanField()
    ca_items = CaItemSerializer(many=True)
    students = WorkspaceStudentSerializer(many=True)


class PublishStudentsSerializer(serializers.Serializer):
    student_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
    )


class ClassTeacherAssessmentRowSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    class_level_id = serializers.UUIDField()
    class_level_name = serializers.CharField()
    stream_id = serializers.UUIDField(allow_null=True)
    stream_name = serializers.CharField(allow_null=True)
    display_name = serializers.CharField()
    students_count = serializers.IntegerField()
    view_stream_id = serializers.UUIDField(allow_null=True)
    pending_count = serializers.IntegerField()
    awaiting_approval_count = serializers.IntegerField()
    approved_count = serializers.IntegerField()


class ClassTeacherAssessmentOverviewSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    pending_count = serializers.IntegerField()
    awaiting_approval_count = serializers.IntegerField()
    approved_count = serializers.IntegerField()
    results = ClassTeacherAssessmentRowSerializer(many=True)


class ApproveClassStudentsSerializer(serializers.Serializer):
    student_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
    )
    remarks = serializers.CharField(required=False, allow_blank=True, default='')


class AssessmentSubjectRowSerializer(serializers.Serializer):
    subject_label = serializers.CharField()
    subject_name = serializers.CharField()
    group_name = serializers.CharField(allow_null=True)
    teacher_name = serializers.CharField(allow_null=True)
    is_published = serializers.BooleanField()
    status = serializers.CharField()
    class_score = serializers.FloatField(allow_null=True)
    exam = serializers.FloatField(allow_null=True)
    total = serializers.FloatField(allow_null=True)
    grade = serializers.CharField(allow_null=True)
    band_remark = serializers.CharField(allow_null=True)
    position = serializers.IntegerField(allow_null=True)
    position_cohort_size = serializers.IntegerField(allow_null=True, required=False)


class ClassAssessmentDetailStudentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    student_id = serializers.CharField()
    status = serializers.CharField()
    subjects_published_count = serializers.IntegerField()
    subjects_required_count = serializers.IntegerField()
    class_teacher_remarks = serializers.CharField(allow_blank=True)
    overall_position = serializers.IntegerField(allow_null=True)
    overall_average = serializers.FloatField(allow_null=True)
    overall_cohort_size = serializers.IntegerField(allow_null=True)
    subjects = AssessmentSubjectRowSerializer(many=True)


class ClassTeacherAssessmentDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    term_id = serializers.UUIDField()
    display_name = serializers.CharField()
    class_level_name = serializers.CharField()
    stream_name = serializers.CharField(allow_null=True)
    class_teacher_name = serializers.CharField(allow_blank=True)
    pending_count = serializers.IntegerField()
    awaiting_approval_count = serializers.IntegerField()
    approved_count = serializers.IntegerField()
    students_count = serializers.IntegerField()
    weights = AssessmentWeightsSerializer()
    result_type = serializers.CharField()
    uses_grades = serializers.BooleanField()
    uses_position = serializers.BooleanField()
    students = ClassAssessmentDetailStudentSerializer(many=True)
