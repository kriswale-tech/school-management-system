from rest_framework import serializers

from shared.helpers import format_phone_number
from schools.models import School, Term


def validate_image(image):
    max_size = 2 * 1024 * 1024  # 2MB

    if image.size > max_size:
        raise serializers.ValidationError('Image must be less than 2MB.')

    allowed = [
        'image/jpeg',
        'image/png',
        'image/webp',
    ]

    if image.content_type not in allowed:
        raise serializers.ValidationError('Only JPG, PNG and WEBP allowed.')

    return image


class SetupSchoolProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = [
            'name',
            'address',
            'gps_address',
            'box_address',
            'phone_number',
            'phone_number_alt',
            'email',
            'logo',
            'motto',
        ]

    def validate_phone_number(self, value):
        try:
            return format_phone_number(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate_phone_number_alt(self, value):
        if not value:
            return value
        try:
            return format_phone_number(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate_logo(self, value):
        if not value:
            return value
        return validate_image(value)


class SetupStepResponseSerializer(serializers.Serializer):
    next_step = serializers.CharField()
    completed_steps = serializers.ListField(child=serializers.CharField())
    is_complete = serializers.BooleanField()
    progress_percentage = serializers.IntegerField()


class TermScheduleItemSerializer(serializers.Serializer):
    term = serializers.ChoiceField(choices=Term.TermChoices.choices)
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, attrs):
        if attrs['start_date'] >= attrs['end_date']:
            raise serializers.ValidationError('Term end date must be after start date.')
        return attrs


class TermScheduleResponseItemSerializer(serializers.Serializer):
    term = serializers.CharField()
    name = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    is_active = serializers.BooleanField()


class AcademicYearTermDataSerializer(serializers.Serializer):
    academic_year = serializers.CharField(allow_null=True)
    start_date = serializers.DateField(allow_null=True)
    end_date = serializers.DateField(allow_null=True)
    is_active = serializers.BooleanField()
    current_term = serializers.ChoiceField(
        choices=Term.TermChoices.choices,
        allow_null=True,
    )
    terms = TermScheduleResponseItemSerializer(many=True)


class SetupAcademicYearTermSerializer(serializers.Serializer):
    academic_year = serializers.CharField(max_length=9)
    current_term = serializers.ChoiceField(choices=Term.TermChoices.choices)
    terms = TermScheduleItemSerializer(many=True)

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
        terms = attrs['terms']
        required_terms = {choice.value for choice in Term.TermChoices}
        provided_terms = {item['term'] for item in terms}

        if provided_terms != required_terms:
            raise serializers.ValidationError({
                'terms': 'First, second and third term schedules are required.',
            })

        terms_by_key = {item['term']: item for item in terms}
        first_term = terms_by_key[Term.TermChoices.FIRST_TERM]
        second_term = terms_by_key[Term.TermChoices.SECOND_TERM]
        third_term = terms_by_key[Term.TermChoices.THIRD_TERM]

        if first_term['end_date'] > second_term['start_date']:
            raise serializers.ValidationError({
                'terms': 'Second term must start on or after first term ends.',
            })

        if second_term['end_date'] > third_term['start_date']:
            raise serializers.ValidationError({
                'terms': 'Third term must start on or after second term ends.',
            })

        expected_label = (
            f"{first_term['start_date'].year}/{third_term['end_date'].year}"
        )
        if attrs['academic_year'] != expected_label:
            raise serializers.ValidationError({
                'academic_year': (
                    f'Academic year must be {expected_label} based on term dates.'
                ),
            })

        attrs['terms_by_key'] = terms_by_key
        return attrs

    def save(self, school):
        from schools.services.academic import save_academic_year_setup

        return save_academic_year_setup(school, self.validated_data)


class SetupAcademicYearTermPostResponseSerializer(
    AcademicYearTermDataSerializer,
    SetupStepResponseSerializer,
):
    pass