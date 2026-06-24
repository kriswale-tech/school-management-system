from rest_framework.views import exception_handler

from shared.exceptions import (
    CloudinaryUploadError,
    cloudinary_error_detail,
    format_error_response,
)


def custom_exception_handler(exc, context):
    try:
        from cloudinary.exceptions import Error as CloudinaryError
    except ImportError:
        CloudinaryError = ()

    if CloudinaryError and isinstance(exc, CloudinaryError):
        api_exc = CloudinaryUploadError(detail=cloudinary_error_detail(exc))
        response = exception_handler(api_exc, context)
        if response is not None:
            response.data = format_error_response(api_exc, response.data)
        return response

    response = exception_handler(exc, context)

    if response is not None:
        response.data = format_error_response(exc, response.data)

    return response
