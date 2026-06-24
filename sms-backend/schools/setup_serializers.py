from rest_framework import serializers

from shared.helpers import format_phone_number
from schools.models import School


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
