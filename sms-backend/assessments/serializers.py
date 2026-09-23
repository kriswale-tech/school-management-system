from decimal import Decimal

from rest_framework import serializers

from schools.setup_serializers.assessment import (
    GradeTemplatesSerializer,
    SetupAssessmentLevelSerializer,
)

from schools.setup_serializers.assessment import (
    GradeTemplatesSerializer,
    SetupAssessmentLevelSerializer,
)


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
    needs_correction = serializers.BooleanField(required=False)
    correction_reason = serializers.CharField(required=False, allow_blank=True)


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
    needs_correction_count = serializers.IntegerField()


class AdminAssessmentTermOptionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    label = serializers.CharField()
    is_active = serializers.BooleanField()
    academic_year_id = serializers.UUIDField()
    academic_year = serializers.CharField()


class AdminAssessmentFilterOptionsSerializer(serializers.Serializer):
    terms = AdminAssessmentTermOptionSerializer(many=True)
    active_term_id = serializers.UUIDField(allow_null=True)


class AdminAssessmentClassRowSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    class_level_id = serializers.UUIDField()
    stream_id = serializers.UUIDField()
    display_name = serializers.CharField()
    class_teacher_name = serializers.CharField(allow_null=True)
    class_teacher_id = serializers.UUIDField(allow_null=True)
    students_count = serializers.IntegerField()
    with_class_teacher_count = serializers.IntegerField()
    ready_for_you_count = serializers.IntegerField()
    released_count = serializers.IntegerField()
    needs_correction_count = serializers.IntegerField(required=False)


class ApproveClassStudentsSerializer(serializers.Serializer):
    student_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
    )
    remarks = serializers.CharField(required=False, allow_blank=True, default='')
    conduct = serializers.CharField(required=False, allow_blank=True, default='')
    attitude = serializers.CharField(required=False, allow_blank=True, default='')
    interest = serializers.CharField(required=False, allow_blank=True, default='')


class AssessmentSubjectRowSerializer(serializers.Serializer):
    teaching_assignment_id = serializers.UUIDField(allow_null=True)
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


class CorrectionSubjectSerializer(serializers.Serializer):
    teaching_assignment_id = serializers.UUIDField()
    subject_label = serializers.CharField()


class CorrectionRequestSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.CharField()
    status = serializers.CharField()
    reason = serializers.CharField()
    previous_result_status = serializers.CharField(allow_null=True)
    student_id = serializers.UUIDField()
    stream_id = serializers.UUIDField()
    term_id = serializers.UUIDField()
    subjects = CorrectionSubjectSerializer(many=True)
    raised_by_name = serializers.CharField(allow_blank=True)
    raised_at = serializers.CharField(allow_null=True)
    reviewed_by_name = serializers.CharField(allow_blank=True)
    reviewed_at = serializers.CharField(allow_null=True)
    applied_at = serializers.CharField(allow_null=True)
    resolved_at = serializers.CharField(allow_null=True)


class CorrectionInboxItemSerializer(CorrectionRequestSerializer):
    student_name = serializers.CharField()
    student_code = serializers.CharField()
    class_name = serializers.CharField()
    class_teacher_id = serializers.UUIDField(allow_null=True)
    term_label = serializers.CharField(allow_null=True)


class AdminAssessmentOverviewSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()
    with_class_teacher_count = serializers.IntegerField()
    ready_for_you_count = serializers.IntegerField()
    released_count = serializers.IntegerField()
    needs_correction_count = serializers.IntegerField(required=False)
    classes_fully_ready_count = serializers.IntegerField()
    corrections_inbox_count = serializers.IntegerField()
    corrections_inbox = CorrectionInboxItemSerializer(many=True)
    results = AdminAssessmentClassRowSerializer(many=True)


class ClassTeacherAssessmentOverviewSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    pending_count = serializers.IntegerField()
    awaiting_approval_count = serializers.IntegerField()
    approved_count = serializers.IntegerField()
    needs_correction_count = serializers.IntegerField()
    corrections_inbox_count = serializers.IntegerField()
    corrections_inbox = CorrectionInboxItemSerializer(many=True)
    results = ClassTeacherAssessmentRowSerializer(many=True)


class CorrectionActionSerializer(serializers.Serializer):
    teaching_assignment_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
    )
    reason = serializers.CharField()


class CorrectionReviewSerializer(serializers.Serializer):
    approve = serializers.BooleanField()


class CorrectionActionResponseSerializer(serializers.Serializer):
    correction = CorrectionRequestSerializer()
    detail = serializers.DictField()


class AdminAssessmentDetailStudentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    student_id = serializers.CharField()
    status = serializers.CharField()
    subjects_published_count = serializers.IntegerField()
    subjects_required_count = serializers.IntegerField()
    class_teacher_remarks = serializers.CharField(allow_blank=True)
    conduct = serializers.CharField(allow_blank=True)
    attitude = serializers.CharField(allow_blank=True)
    interest = serializers.CharField(allow_blank=True)
    head_teacher_remarks = serializers.CharField(allow_blank=True)
    overall_position = serializers.IntegerField(allow_null=True)
    overall_average = serializers.FloatField(allow_null=True)
    overall_cohort_size = serializers.IntegerField(allow_null=True)
    subjects = AssessmentSubjectRowSerializer(many=True)
    active_correction = CorrectionRequestSerializer(allow_null=True)


class AdminAssessmentDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()
    display_name = serializers.CharField()
    class_teacher_name = serializers.CharField(allow_null=True, allow_blank=True)
    with_class_teacher_count = serializers.IntegerField()
    ready_for_you_count = serializers.IntegerField()
    released_count = serializers.IntegerField()
    needs_correction_count = serializers.IntegerField()
    pending_reopen_requests_count = serializers.IntegerField()
    students_count = serializers.IntegerField()
    weights = AssessmentWeightsSerializer()
    result_type = serializers.CharField()
    uses_grades = serializers.BooleanField()
    uses_position = serializers.BooleanField()
    students = AdminAssessmentDetailStudentSerializer(many=True)


class ClassAssessmentDetailStudentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    student_id = serializers.CharField()
    status = serializers.CharField()
    is_released = serializers.BooleanField()
    subjects_published_count = serializers.IntegerField()
    subjects_required_count = serializers.IntegerField()
    class_teacher_remarks = serializers.CharField(allow_blank=True)
    conduct = serializers.CharField(allow_blank=True)
    attitude = serializers.CharField(allow_blank=True)
    interest = serializers.CharField(allow_blank=True)
    overall_position = serializers.IntegerField(allow_null=True)
    overall_average = serializers.FloatField(allow_null=True)
    overall_cohort_size = serializers.IntegerField(allow_null=True)
    subjects = AssessmentSubjectRowSerializer(many=True)
    active_correction = CorrectionRequestSerializer(allow_null=True)


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
    needs_correction_count = serializers.IntegerField()
    students_count = serializers.IntegerField()
    weights = AssessmentWeightsSerializer()
    result_type = serializers.CharField()
    uses_grades = serializers.BooleanField()
    uses_position = serializers.BooleanField()
    students = ClassAssessmentDetailStudentSerializer(many=True)


class ReportSchoolSerializer(serializers.Serializer):
    name = serializers.CharField()
    box_address = serializers.CharField(allow_blank=True)
    address = serializers.CharField(allow_blank=True)
    phone_number = serializers.CharField(allow_blank=True)
    phone_number_alt = serializers.CharField(allow_blank=True)
    email = serializers.CharField(allow_blank=True)
    motto = serializers.CharField(allow_blank=True)
    logo_url = serializers.CharField(allow_null=True)


class ReportSubjectRowSerializer(serializers.Serializer):
    subject_label = serializers.CharField()
    class_score = serializers.FloatField()
    exam_score = serializers.FloatField()
    total = serializers.FloatField()
    grade = serializers.CharField(allow_null=True)
    remark = serializers.CharField(allow_null=True)


class ReportTotalsSerializer(serializers.Serializer):
    class_score = serializers.FloatField(allow_null=True)
    exam_score = serializers.FloatField(allow_null=True)
    total = serializers.FloatField(allow_null=True)
    max_class_score = serializers.FloatField(allow_null=True)
    max_exam_score = serializers.FloatField(allow_null=True)
    max_total = serializers.FloatField(allow_null=True)


class ReportGradeBandSerializer(serializers.Serializer):
    grade = serializers.CharField()
    min_score = serializers.IntegerField()
    max_score = serializers.IntegerField()
    remark = serializers.CharField()


class StudentReportPreviewSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    stream_id = serializers.UUIDField()
    term_id = serializers.UUIDField()
    school = ReportSchoolSerializer()
    report_title = serializers.CharField()
    student_name = serializers.CharField()
    class_name = serializers.CharField()
    academic_year = serializers.CharField()
    term_label = serializers.CharField()
    next_term_begins = serializers.CharField(allow_null=True)
    students_on_roll = serializers.IntegerField()
    position = serializers.IntegerField(allow_null=True)
    position_label = serializers.CharField(allow_null=True)
    uses_position = serializers.BooleanField()
    uses_grades = serializers.BooleanField()
    weights = AssessmentWeightsSerializer()
    subjects = ReportSubjectRowSerializer(many=True)
    totals = ReportTotalsSerializer()
    conduct = serializers.CharField(allow_blank=True)
    attitude = serializers.CharField(allow_blank=True)
    interest = serializers.CharField(allow_blank=True)
    class_teacher_remarks = serializers.CharField(allow_blank=True)
    head_teacher_remarks = serializers.CharField(allow_blank=True)
    class_teacher_name = serializers.CharField(allow_blank=True)
    grade_bands = ReportGradeBandSerializer(many=True)


class StoredStudentReportSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    student_id = serializers.UUIDField()
    stream_id = serializers.UUIDField()
    term_id = serializers.UUIDField()
    generated_at = serializers.CharField(allow_null=True)
    url = serializers.CharField(allow_null=True)
    url_expires_in = serializers.IntegerField()
    status = serializers.CharField()


class AssessmentSettingsTermOptionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    label = serializers.CharField()
    is_active = serializers.BooleanField()
    is_ended = serializers.BooleanField()
    academic_year_id = serializers.UUIDField()
    academic_year = serializers.CharField()


class AssessmentSettingsSerializer(serializers.Serializer):
    grade_templates = GradeTemplatesSerializer()
    levels = SetupAssessmentLevelSerializer(many=True)
    term_id = serializers.UUIDField()
    term_ended = serializers.BooleanField()
    is_editable = serializers.BooleanField()
    has_recorded_marks = serializers.BooleanField()
    terms = AssessmentSettingsTermOptionSerializer(many=True)
    active_term_id = serializers.UUIDField(allow_null=True)
