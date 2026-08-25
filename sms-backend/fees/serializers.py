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


class StudentPaymentTargetSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    student = PaymentTargetStudentSerializer()
    target_term = PaymentTargetTermSerializer(allow_null=True)
    outstanding_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    has_outstanding = serializers.BooleanField()
    advance_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    has_advance = serializers.BooleanField()


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


class FeeStructureSettingsSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    is_editable = serializers.BooleanField()
    is_locked = serializers.BooleanField()
    term_ended = serializers.BooleanField()
    can_apply = serializers.BooleanField()
    item_count = serializers.IntegerField()
    term_id = serializers.UUIDField()
    term_name = serializers.CharField()
    academic_year = serializers.CharField()
    applied_at = serializers.DateTimeField(allow_null=True)


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

