from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from platform_admin.models import PlatformUser
from platform_admin.tokens import MFA_PENDING_CLAIM, PLATFORM_REALM, REALM_CLAIM


class PlatformJWTCookieAuthentication(JWTAuthentication):
    """Authenticate platform operators from platform_* JWT cookies."""

    def authenticate(self, request):
        raw_token = request.COOKIES.get(settings.PLATFORM_JWT['AUTH_COOKIE'])
        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
        except TokenError:
            return None

        if validated_token.get(REALM_CLAIM) != PLATFORM_REALM:
            return None
        if validated_token.get(MFA_PENDING_CLAIM):
            return None

        user = self.get_platform_user(validated_token)
        request.platform_user = user
        return user, validated_token

    def get_platform_user(self, validated_token) -> PlatformUser:
        user_id = validated_token.get('user_id')
        if not user_id:
            raise InvalidToken('Token contained no recognizable platform user identification')
        try:
            user = PlatformUser.objects.get(pk=user_id)
        except PlatformUser.DoesNotExist as exc:
            raise InvalidToken('User not found') from exc
        if not user.is_active:
            raise InvalidToken('User is inactive')
        return user


class PlatformMfaPendingAuthentication(JWTAuthentication):
    """Accept only short-lived MFA-pending tokens (Authorization Bearer or cookie)."""

    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            raw_token = self.get_raw_token(header)
        else:
            raw_token = request.COOKIES.get(settings.PLATFORM_JWT['AUTH_COOKIE'])

        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
        except TokenError:
            return None

        if validated_token.get(REALM_CLAIM) != PLATFORM_REALM:
            return None
        if not validated_token.get(MFA_PENDING_CLAIM):
            return None

        user_id = validated_token.get('user_id')
        try:
            user = PlatformUser.objects.get(pk=user_id, is_active=True)
        except PlatformUser.DoesNotExist as exc:
            raise InvalidToken('User not found') from exc

        request.platform_user = user
        return user, validated_token
