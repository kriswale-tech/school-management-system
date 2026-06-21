from django.conf import settings


def _cookie_kwargs(max_age: int) -> dict:
    return {
        'httponly': settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
        'secure': settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
        'samesite': settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
        'path': settings.SIMPLE_JWT['AUTH_COOKIE_PATH'],
        'max_age': max_age,
    }


def set_auth_cookies(response, access_token: str, refresh_token: str) -> None:
    jwt_settings = settings.SIMPLE_JWT

    response.set_cookie(
        key=jwt_settings['AUTH_COOKIE'],
        value=access_token,
        **_cookie_kwargs(int(jwt_settings['ACCESS_TOKEN_LIFETIME'].total_seconds())),
    )
    response.set_cookie(
        key=jwt_settings['AUTH_COOKIE_REFRESH'],
        value=refresh_token,
        **_cookie_kwargs(int(jwt_settings['REFRESH_TOKEN_LIFETIME'].total_seconds())),
    )


def clear_auth_cookies(response) -> None:
    jwt_settings = settings.SIMPLE_JWT

    for key in (jwt_settings['AUTH_COOKIE'], jwt_settings['AUTH_COOKIE_REFRESH']):
        response.delete_cookie(
            key=key,
            path=jwt_settings['AUTH_COOKIE_PATH'],
            samesite=jwt_settings['AUTH_COOKIE_SAMESITE'],
        )