from rest_framework.exceptions import APIException


class BaseAPIException(APIException):
    """API exception with an explicit machine-readable error_code."""

    error_code = 'api_error'

    def __init__(self, detail=None, error_code=None):
        if error_code is not None:
            self.error_code = error_code
        super().__init__(detail)


class CloudinaryUploadError(BaseAPIException):
    status_code = 400
    default_detail = 'Image upload failed.'
    error_code = 'cloudinary_upload_failed'


def cloudinary_error_detail(exc) -> str:
    from cloudinary.exceptions import NotAllowed

    if isinstance(exc, NotAllowed):
        return (
            'Image upload is not allowed with the current Cloudinary credentials. '
            'Use an API key with upload permission, or set CLOUDINARY_UPLOAD_PRESET '
            'for unsigned uploads.'
        )

    message = str(exc).lower()
    if 'invalid api key' in message:
        return 'Invalid Cloudinary API credentials.'
    if 'file size' in message or 'too large' in message:
        return 'Image file is too large for upload.'

    return 'Image upload failed. Please try again.'


def get_error_code(exc):
    if hasattr(exc, "error_code") and exc.error_code:
        return str(exc.error_code).upper()
    if hasattr(exc, "default_code") and exc.default_code:
        return str(exc.default_code).upper()
    return "API_ERROR"


def extract_detail(raw_detail):
    if raw_detail is None:
        return "An error occurred."

    if isinstance(raw_detail, str):
        return raw_detail

    if isinstance(raw_detail, list):
        if not raw_detail:
            return "An error occurred."
        return "; ".join(str(item) for item in raw_detail)

    if isinstance(raw_detail, dict):
        if "detail" in raw_detail:
            return extract_detail(raw_detail["detail"])

        if "non_field_errors" in raw_detail:
            return extract_detail(raw_detail["non_field_errors"])

        messages = []
        for field, errors in raw_detail.items():
            if isinstance(errors, list):
                for error in errors:
                    messages.append(f"{field}: {error}")
            else:
                messages.append(f"{field}: {errors}")

        if messages:
            return "; ".join(messages)

    return "An error occurred."


def format_error_response(exc, raw_detail):
    return {
        "success": False,
        "error_code": get_error_code(exc),
        "detail": extract_detail(raw_detail),
        "raw_detail": raw_detail,
    }
