from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from fees.models import FeeItem


class SetupFeeItemSerializer(serializers.Serializer):
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


class SetupFeeStructureSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    is_editable = serializers.BooleanField()
    is_locked = serializers.BooleanField()
    term_id = serializers.UUIDField()
    term_name = serializers.CharField()
    academic_year = serializers.CharField()


class SetupFeesDataSerializer(serializers.Serializer):
    fee_structure = SetupFeeStructureSerializer()
    fee_items = SetupFeeItemSerializer(many=True)


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
                'applies_to_id': (
                    'Level and class fees must specify an applies_to_id.'
                ),
            })

        return attrs


class CreateFeeItemSerializer(FeeItemWriteSerializer):
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


class UpdateFeeItemSerializer(FeeItemWriteSerializer):
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
