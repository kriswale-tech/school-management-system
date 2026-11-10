from django.conf import settings


def _cookie_kwargs(max_age: int) -> dict:
    cfg = settings.PLATFORM_JWT
    return {
        'httponly': cfg['AUTH_COOKIE_HTTP_ONLY'],
        'secure': cfg['AUTH_COOKIE_SECURE'],
        'samesite': cfg['AUTH_COOKIE_SAMESITE'],
        'path': cfg['AUTH_COOKIE_PATH'],
        'max_age': max_age,
    }


def set_platform_auth_cookies(response, access_token: str, refresh_token: str) -> None:
    cfg = settings.PLATFORM_JWT
    response.set_cookie(
        key=cfg['AUTH_COOKIE'],
        value=access_token,
        **_cookie_kwargs(int(cfg['ACCESS_TOKEN_LIFETIME'].total_seconds())),
    )
    response.set_cookie(
        key=cfg['AUTH_COOKIE_REFRESH'],
        value=refresh_token,
        **_cookie_kwargs(int(cfg['REFRESH_TOKEN_LIFETIME'].total_seconds())),
    )


def clear_platform_auth_cookies(response) -> None:
    cfg = settings.PLATFORM_JWT
    for key in (cfg['AUTH_COOKIE'], cfg['AUTH_COOKIE_REFRESH']):
        response.delete_cookie(
            key=key,
            path=cfg['AUTH_COOKIE_PATH'],
            samesite=cfg['AUTH_COOKIE_SAMESITE'],
        )
