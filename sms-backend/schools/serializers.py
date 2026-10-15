import re

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from schools.services.setup import OPTIONAL_SETUP_STEP_VALUES
from schools.setup_serializers.school_profile import SetupSchoolProfileSerializer

from .models import School, SchoolSettings, SchoolSetup, Term


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = '__all__'

    read_only_fields = ['id', 'setup_completed', 'setup_completed_at']


class SchoolProfileUpdateSerializer(SetupSchoolProfileSerializer):
    class Meta(SetupSchoolProfileSerializer.Meta):
        fields = SetupSchoolProfileSerializer.Meta.fields + ['student_id_prefix']

    def validate_student_id_prefix(self, value):
        prefix = (value or '').strip().upper()
        if not prefix:
            return ''
        if not re.fullmatch(r'[A-Z0-9]{2,12}', prefix):
            raise serializers.ValidationError('Prefix must be 2–12 letters or numbers.')
        return prefix


class SchoolSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolSettings
        fields = [
            'fees_alert_enabled',
            'fees_alert_threshold',
            'results_alert_enabled',
            'enrollments_alert_enabled',
            'transition_popup_enabled',
            'report_show_logo',
            'report_show_address',
            'report_show_phones',
            'report_show_email',
        ]

    def validate_fees_alert_threshold(self, value):
        if value < 0:
            raise serializers.ValidationError('Threshold must be zero or greater.')
        return value


class CalendarTermSerializer(serializers.Serializer):
    id = serializers.UUIDField(allow_null=True)
    term = serializers.CharField()
    name = serializers.CharField()
    start_date = serializers.DateField(allow_null=True)
    end_date = serializers.DateField(allow_null=True)
    is_active = serializers.BooleanField()
    is_ended = serializers.BooleanField()
    can_edit_dates = serializers.BooleanField()
    is_next = serializers.BooleanField()


class CalendarYearSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    academic_year = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    is_active = serializers.BooleanField()
    status = serializers.CharField()
    terms = CalendarTermSerializer(many=True)


class AcademicYearCalendarSerializer(serializers.Serializer):
    years = CalendarYearSerializer(many=True)
    next_year_label = serializers.CharField(allow_null=True)
    active_term_id = serializers.UUIDField(allow_null=True)


class AcademicYearScheduleTermSerializer(serializers.Serializer):
    term = serializers.ChoiceField(choices=Term.TermChoices.choices)
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class AcademicYearScheduleSerializer(serializers.Serializer):
    academic_year = serializers.CharField(max_length=9)
    terms = AcademicYearScheduleTermSerializer(many=True)

    def validate_academic_year(self, value):
        if len(value) != 9 or value[4] != '/':
            raise serializers.ValidationError('Academic year must be in YYYY/YYYY format.')
        start_year, end_year = value.split('/')
        if not (start_year.isdigit() and end_year.isdigit()):
            raise serializers.ValidationError('Academic year must be in YYYY/YYYY format.')
        if int(end_year) != int(start_year) + 1:
            raise serializers.ValidationError(
                'Academic year end must be one year after the start year.'
            )
        return value

    def validate(self, attrs):
        provided = {item['term'] for item in attrs['terms']}
        required = {choice.value for choice in Term.TermChoices}
        if provided != required:
            raise serializers.ValidationError({
                'terms': 'First, second and third term dates are required.',
            })
        return attrs


class TermSwitchSerializer(serializers.Serializer):
    acknowledge_warnings = serializers.BooleanField(required=False, default=False)


class TermSwitchPreviewSerializer(serializers.Serializer):
    can_switch = serializers.BooleanField()
    blockers = serializers.ListField(child=serializers.CharField())
    warnings = serializers.ListField(child=serializers.CharField())
    term_id = serializers.UUIDField()
    term_label = serializers.CharField()


class TransitionStreamChoiceSerializer(serializers.Serializer):
    source_stream_id = serializers.UUIDField()
    destination_stream_id = serializers.UUIDField()


class TransitionConfirmSerializer(serializers.Serializer):
    acknowledge_warnings = serializers.BooleanField(required=False, default=False)
    stream_choices = TransitionStreamChoiceSerializer(many=True, required=False, default=list)


class SchoolAlertSerializer(serializers.Serializer):
    kind = serializers.CharField()
    title = serializers.CharField()
    summary = serializers.CharField()
    count = serializers.IntegerField()
    href = serializers.CharField()


class SchoolSetupStepSerializer(serializers.Serializer):
    step = serializers.CharField()
    name = serializers.CharField()
    completed = serializers.BooleanField()
    required = serializers.BooleanField()


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
                'required': value not in OPTIONAL_SETUP_STEP_VALUES,
            }
            for value, label in SchoolSetup.SetupStep.choices
            if value != SchoolSetup.SetupStep.COMPLETED
        ]
