import secrets

from rest_framework.exceptions import ValidationError

from shared.exceptions import cloudinary_error_detail


def generate_otp():
    return str(secrets.randbelow(900000) + 100000)


def save_user_serializer(serializer):
    try:
        return serializer.save()
    except Exception as exc:
        from cloudinary.exceptions import Error as CloudinaryError

        if isinstance(exc, CloudinaryError):
            raise ValidationError({
                'profile_picture': cloudinary_error_detail(exc),
            }) from exc
        raise
