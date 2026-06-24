from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import School, SchoolSetup


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = '__all__'

    read_only_fields = ['id', 'setup_completed', 'setup_completed_at']


class SchoolSetupStepSerializer(serializers.Serializer):
    step = serializers.CharField()
    name = serializers.CharField()
    completed = serializers.BooleanField()


class SchoolSetupSerializer(serializers.ModelSerializer):
    steps = serializers.SerializerMethodField()

    class Meta:
        model = SchoolSetup
        exclude = ['completed_steps']

    @extend_schema_field(SchoolSetupStepSerializer(many=True))
    def get_steps(self, obj):
        completed = set(obj.completed_steps or [])
        return [
            {
                'step': value,
                'name': label,
                'completed': value in completed,
            }
            for value, label in SchoolSetup.SetupStep.choices
            if value != SchoolSetup.SetupStep.COMPLETED
        ]
