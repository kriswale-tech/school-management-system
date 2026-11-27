"""Environment-aware upload paths with stable Django migration state."""

from django.conf import settings


def profile_picture_upload_to(instance, filename):
    return f'{settings.PARENT_CLOUDINARY_FOLDER}/profile-pictures/{filename}'


def school_logo_upload_to(instance, filename):
    return f'{settings.PARENT_CLOUDINARY_FOLDER}/school-logos/{filename}'
