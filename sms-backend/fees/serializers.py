from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from fees.models import FeeItem, Payment
from students.serializers import StudentClassLevelSerializer, StudentStreamSerializer


class FeeDeskRowSerializer(serializers.Serializer):
    id = serializers.UUIDField(source='student.id')
    student_id = serializers.CharField(source='student.student_id')
    first_name = serializers.CharField(source='student.first_name')
    last_name = serializers.CharField(source='student.last_name')
    other_names = serializers.CharField(source='student.other_names')
    class_level = StudentClassLevelSerializer()
    stream = StudentStreamSerializer()
    amount_paid = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        source='total_paid',
    )
    remaining_balance = serializers.SerializerMethodField()
    advance_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    last_transaction_at = serializers.DateTimeField(allow_null=True)
    payment_status = serializers.CharField()

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_remaining_balance(self, obj):
        billed = getattr(obj, 'total_billed', None) or Decimal('0.00')
        paid = getattr(obj, 'total_paid', None) or Decimal('0.00')
        return max(billed - paid, Decimal('0.00'))


class FeeDeskStatsSerializer(serializers.Serializer):
    total_expected = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_collected = serializers.DecimalField(max_digits=14, decimal_places=2)
    outstanding = serializers.DecimalField(max_digits=14, decimal_places=2)
    debtors_count = serializers.IntegerField()
    total_students = serializers.IntegerField()
    students_in_credit = serializers.IntegerField()
    total_advances = serializers.DecimalField(max_digits=14, decimal_places=2)


class FeeDeskTermOptionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    term = serializers.CharField()
    term_name = serializers.CharField()
    label = serializers.CharField()
    is_active = serializers.BooleanField()
    is_ended = serializers.BooleanField()
    has_fee_structure = serializers.BooleanField()
    academic_year_id = serializers.UUIDField()
    academic_year = serializers.CharField()


class FeeDeskAcademicYearSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    academic_year = serializers.CharField()
    is_active = serializers.BooleanField()
    terms = FeeDeskTermOptionSerializer(many=True)


class FeeDeskFilterOptionsSerializer(serializers.Serializer):
    academic_years = FeeDeskAcademicYearSerializer(many=True)
    terms = FeeDeskTermOptionSerializer(many=True)
    active_term_id = serializers.UUIDField(allow_null=True)


class PaymentTargetStudentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    student_id = serializers.CharField()
    full_name = serializers.CharField()
    class_display = serializers.CharField(allow_null=True)


class PaymentTargetTermSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    term = serializers.CharField()
    term_name = serializers.CharField()
    academic_year_id = serializers.UUIDField()
    academic_year = serializers.CharField()
    label = serializers.CharField()


class OutstandingTermBalanceSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)


class StudentPaymentTargetSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    student = PaymentTargetStudentSerializer()
    target_term = PaymentTargetTermSerializer(allow_null=True)
    outstanding_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    has_outstanding = serializers.BooleanField()
    all_time_outstanding = serializers.DecimalField(max_digits=12, decimal_places=2)
    has_all_time_outstanding = serializers.BooleanField()
    outstanding_terms = OutstandingTermBalanceSerializer(many=True)
    advance_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    has_advance = serializers.BooleanField()


class DebtReminderRequestSerializer(serializers.Serializer):
    term_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    student_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
    )


class FeeDeskSelectionIdsSerializer(serializers.Serializer):
    student_ids = serializers.ListField(child=serializers.UUIDField())
    count = serializers.IntegerField()


class DebtReminderGuardianPlanSerializer(serializers.Serializer):
    parent_id = serializers.CharField()
    parent_name = serializers.CharField()
    channels = serializers.ListField(child=serializers.CharField())


class DebtReminderEligibleSerializer(serializers.Serializer):
    student_id = serializers.CharField()
    full_name = serializers.CharField()
    student_code = serializers.CharField()
    balance = serializers.CharField()
    terms_summary = serializers.CharField(required=False, allow_null=True)
    guardians = DebtReminderGuardianPlanSerializer(many=True)


class DebtReminderSkippedSerializer(serializers.Serializer):
    student_id = serializers.CharField()
    full_name = serializers.CharField(required=False)
    balance = serializers.CharField(required=False)
    reason = serializers.CharField()


class DebtReminderPreviewSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    audience = serializers.CharField()
    channels = serializers.CharField(allow_null=True)
    all_time = serializers.BooleanField()
    term_id = serializers.CharField()
    term_label = serializers.CharField()
    requested_count = serializers.IntegerField()
    eligible_count = serializers.IntegerField()
    skipped_count = serializers.IntegerField()
    sms_count = serializers.IntegerField()
    email_count = serializers.IntegerField()
    batch_size = serializers.IntegerField()
    eligible_ids = serializers.ListField(child=serializers.CharField())
    eligible = DebtReminderEligibleSerializer(many=True)
    skipped = DebtReminderSkippedSerializer(many=True)
    eligible_truncated = serializers.BooleanField()
    skipped_truncated = serializers.BooleanField()
    sample_sms = serializers.CharField(allow_blank=True)
    sample_email_subject = serializers.CharField(allow_blank=True)
    sample_email_body = serializers.CharField(allow_blank=True)


class DebtReminderSendResultSerializer(serializers.Serializer):
    batch_id = serializers.CharField()
    all_time = serializers.BooleanField()
    term_id = serializers.CharField()
    term_label = serializers.CharField()
    queued = serializers.BooleanField()
    students_notified = serializers.IntegerField()
    sms_sent = serializers.IntegerField()
    email_sent = serializers.IntegerField()
    skipped_count = serializers.IntegerField()


class ReceiptAllocationSerializer(serializers.Serializer):
    term_label = serializers.CharField()
    amount = serializers.CharField()


class ReceiptDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    school_name = serializers.CharField()
    school_logo_url = serializers.CharField(allow_null=True, required=False)
    school_phone = serializers.CharField(allow_blank=True, allow_null=True)
    school_email = serializers.CharField(allow_blank=True)
    school_address = serializers.CharField(allow_blank=True)
    student_name = serializers.CharField()
    student_id = serializers.CharField()
    receipt_number = serializers.CharField()
    amount = serializers.CharField()
    payment_method = serializers.CharField()
    payment_reference = serializers.CharField(allow_blank=True)
    paid_at = serializers.DateTimeField()
    issued_at = serializers.DateTimeField()
    received_by = serializers.CharField(allow_blank=True)
    term_label = serializers.CharField()
    allocations = ReceiptAllocationSerializer(many=True)


class RecordPaymentSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_method = serializers.ChoiceField(
        choices=[
            choice
            for choice in Payment.PaymentMethod.choices
            if choice[0] != Payment.PaymentMethod.ADVANCE_CREDIT
        ],
    )
    paid_at = serializers.DateTimeField()
    payment_reference = serializers.CharField(required=False, allow_blank=True, default='')
    payment_notes = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Payment amount must be greater than zero.')
        return value


class PaymentAllocationSerializer(serializers.Serializer):
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class RecordPaymentResponseSerializer(serializers.Serializer):
    payment_id = serializers.UUIDField()
    receipt_id = serializers.UUIDField()
    receipt_number = serializers.CharField()
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    amount_applied = serializers.DecimalField(max_digits=10, decimal_places=2)
    advance_created = serializers.DecimalField(max_digits=10, decimal_places=2)
    outstanding_after = serializers.DecimalField(max_digits=12, decimal_places=2)
    advance_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    credit_id = serializers.UUIDField(allow_null=True)
    paid_at = serializers.DateTimeField()
    allocations = PaymentAllocationSerializer(many=True)


class FeeStructureSettingsSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    is_editable = serializers.BooleanField()
    is_locked = serializers.BooleanField()
    term_ended = serializers.BooleanField()
    can_publish = serializers.BooleanField()
    can_apply = serializers.BooleanField()
    can_copy_from_previous = serializers.BooleanField()
    item_count = serializers.IntegerField()
    term_id = serializers.UUIDField()
    term_name = serializers.CharField()
    academic_year = serializers.CharField()
    applied_at = serializers.DateTimeField(allow_null=True)


class NextTermFeePrepSerializer(serializers.Serializer):
    visible = serializers.BooleanField()
    done = serializers.BooleanField()
    urgency = serializers.CharField(allow_null=True)
    days_remaining = serializers.IntegerField(allow_null=True)
    term_ends_on = serializers.CharField(allow_null=True)
    current_term_label = serializers.CharField(allow_null=True)
    next_term_id = serializers.CharField(allow_null=True)
    next_term_label = serializers.CharField(allow_null=True)
    fee_status = serializers.CharField(allow_null=True)
    item_count = serializers.IntegerField()
    summary = serializers.CharField(allow_blank=True)
    href = serializers.CharField()


class FeeItemSettingsSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    description = serializers.CharField()
    applies_to_type = serializers.ChoiceField(choices=FeeItem.AppliesToType.choices)
    applies_to_type_display = serializers.CharField()
    applies_to_id = serializers.UUIDField(allow_null=True)
    applies_to_name = serializers.CharField(allow_null=True)
    student_type = serializers.ChoiceField(choices=FeeItem.StudentType.choices)
    student_type_display = serializers.CharField()
    term_id = serializers.UUIDField()
    term_name = serializers.CharField()
    academic_year = serializers.CharField()


class FeeStructureDetailSerializer(serializers.Serializer):
    fee_structure = FeeStructureSettingsSerializer()
    fee_items = FeeItemSettingsSerializer(many=True)


class FeeItemWriteSerializer(serializers.Serializer):
    applies_to_type = serializers.ChoiceField(choices=FeeItem.AppliesToType.choices)
    applies_to_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        applies_to_type = attrs.get('applies_to_type')
        applies_to_id = attrs.get('applies_to_id')

        if applies_to_type == FeeItem.AppliesToType.SCHOOL:
            attrs['applies_to_id'] = None
        elif applies_to_type in {
            FeeItem.AppliesToType.LEVEL,
            FeeItem.AppliesToType.CLASS,
        } and not applies_to_id:
            raise serializers.ValidationError({
                'applies_to_id': 'Level and class fees must specify an applies_to_id.',
            })

        return attrs


class CreateFeeStructureItemSerializer(FeeItemWriteSerializer):
    name = serializers.CharField(max_length=255)
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0'),
    )
    description = serializers.CharField(required=False, allow_blank=True, default='')
    student_type = serializers.ChoiceField(
        choices=FeeItem.StudentType.choices,
        default=FeeItem.StudentType.ALL_STUDENTS,
    )
    term = serializers.UUIDField(required=False)


class UpdateFeeStructureItemSerializer(FeeItemWriteSerializer):
    name = serializers.CharField(max_length=255, required=False)
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0'),
        required=False,
    )
    description = serializers.CharField(required=False, allow_blank=True)
    applies_to_type = serializers.ChoiceField(
        choices=FeeItem.AppliesToType.choices,
        required=False,
    )
    student_type = serializers.ChoiceField(
        choices=FeeItem.StudentType.choices,
        required=False,
    )

    def validate(self, attrs):
        if 'applies_to_type' not in attrs:
            return attrs
        return super().validate(attrs)

