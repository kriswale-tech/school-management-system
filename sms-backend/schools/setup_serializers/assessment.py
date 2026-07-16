from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from assessments.models import AssessmentConfig
from assessments.services.assessment_config import validate_grade_bands


class GradeBandTemplateSerializer(serializers.Serializer):
    grade = serializers.CharField()
    min_score = serializers.IntegerField()
    max_score = serializers.IntegerField()
    remark = serializers.CharField()


class SetupGradeBandSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    grade = serializers.CharField()
    min_score = serializers.IntegerField()
    max_score = serializers.IntegerField()
    remark = serializers.CharField()


class SetupAssessmentConfigSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    continuous_assessment_weight = serializers.DecimalField(max_digits=5, decimal_places=2)
    exam_weight = serializers.DecimalField(max_digits=5, decimal_places=2)
    result_type = serializers.ChoiceField(choices=AssessmentConfig.ResultType.choices)
    grade_type = serializers.ChoiceField(
        choices=AssessmentConfig.GradeType.choices,
        allow_null=True,
    )
    grade_bands = SetupGradeBandSerializer(many=True)


class SetupAssessmentLevelSerializer(serializers.Serializer):
    level_id = serializers.UUIDField()
    level_name = serializers.CharField()
    level_order = serializers.IntegerField()
    config = SetupAssessmentConfigSerializer(allow_null=True)


class GradeTemplatesSerializer(serializers.Serializer):
    letter = GradeBandTemplateSerializer(many=True)
    numerical = GradeBandTemplateSerializer(many=True)


class SetupAssessmentDataSerializer(serializers.Serializer):
    grade_templates = GradeTemplatesSerializer()
    levels = SetupAssessmentLevelSerializer(many=True)


class SaveGradeBandSerializer(serializers.Serializer):
    grade = serializers.CharField(max_length=10)
    min_score = serializers.IntegerField(min_value=0, max_value=100)
    max_score = serializers.IntegerField(min_value=0, max_value=100)
    remark = serializers.CharField(max_length=100)


class SaveLevelAssessmentConfigSerializer(serializers.Serializer):
    continuous_assessment_weight = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal('0'),
    )
    exam_weight = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal('0'),
    )
    result_type = serializers.ChoiceField(choices=AssessmentConfig.ResultType.choices)
    grade_type = serializers.ChoiceField(
        choices=AssessmentConfig.GradeType.choices,
        required=False,
        allow_null=True,
    )
    grade_bands = SaveGradeBandSerializer(many=True, required=False)

    def validate(self, attrs):
        ca_weight = attrs['continuous_assessment_weight']
        exam_weight = attrs['exam_weight']
        if ca_weight + exam_weight != Decimal('100'):
            raise serializers.ValidationError({
                'continuous_assessment_weight': (
                    'Continuous assessment and exam weights must sum to 100.'
                ),
            })

        result_type = attrs['result_type']
        uses_grades = result_type in AssessmentConfig.GRADE_RESULT_TYPES
        grade_type = attrs.get('grade_type')
        grade_bands = attrs.get('grade_bands') or []

        if uses_grades:
            if not grade_type:
                raise serializers.ValidationError({
                    'grade_type': (
                        'Grade type is required when result type includes grades.'
                    ),
                })
            if not grade_bands:
                raise serializers.ValidationError({
                    'grade_bands': (
                        'Grade bands are required when result type includes grades.'
                    ),
                })
            try:
                validate_grade_bands(grade_bands)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({
                    'grade_bands': list(exc.messages),
                }) from exc
        else:
            attrs['grade_type'] = None
            attrs['grade_bands'] = []

        return attrs
