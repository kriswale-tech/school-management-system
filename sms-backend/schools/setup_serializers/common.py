from rest_framework import serializers


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


class SetupStepResponseSerializer(serializers.Serializer):
    next_step = serializers.CharField()
    completed_steps = serializers.ListField(child=serializers.CharField())
    is_complete = serializers.BooleanField()
    progress_percentage = serializers.IntegerField()
