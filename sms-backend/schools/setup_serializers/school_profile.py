from rest_framework import serializers

from shared.helpers import format_phone_number
from schools.models import School
from schools.setup_serializers.common import validate_image


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
