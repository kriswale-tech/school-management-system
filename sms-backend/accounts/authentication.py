from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError

from accounts.services.memberships import get_active_membership
from accounts.tokens import token_school_id


class JWTCookieAuthentication(JWTAuthentication):
    def authenticate(self, request):
        raw_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE'])

        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
        except TokenError:
            return None

        user = self.get_user(validated_token)
        self._attach_school_scope(request, user, validated_token)
        return user, validated_token

    def _attach_school_scope(self, request, user, validated_token) -> None:
        """Resolve the token's school claim onto the request.

        Resolution is lenient: a claim whose membership has since been revoked
        leaves the request unscoped rather than failing authentication, so the
        user can still reach /me/, school selection, and logout.
        """
        request.membership = None
        request.membership_revoked = False

        school_id = token_school_id(validated_token)
        if not school_id:
            return

        membership = get_active_membership(user, school_id)
        if membership is None:
            request.membership_revoked = True
            return

        request.membership = membership
