import logging
from datetime import timedelta

from django.conf import settings
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from platform_admin.models import PlatformUser

logger = logging.getLogger(__name__)

REALM_CLAIM = 'realm'
ROLE_CLAIM = 'role'
MFA_PENDING_CLAIM = 'mfa_pending'
PLATFORM_REALM = 'platform'


class PlatformRefreshToken(RefreshToken):
    """Refresh token whose user_id refers to PlatformUser, not AUTH_USER_MODEL."""


def build_platform_token(user: PlatformUser) -> RefreshToken:
    refresh = PlatformRefreshToken()
    refresh['user_id'] = str(user.pk)
    refresh[REALM_CLAIM] = PLATFORM_REALM
    refresh[ROLE_CLAIM] = user.role
    refresh[MFA_PENDING_CLAIM] = False
    return refresh


def build_mfa_pending_token(user: PlatformUser) -> AccessToken:
    """Short-lived access token used only to complete MFA after password login."""
    token = AccessToken()
    token.set_exp(
        lifetime=timedelta(minutes=settings.PLATFORM_MFA_PENDING_MINUTES),
    )
    token['user_id'] = str(user.pk)
    token[REALM_CLAIM] = PLATFORM_REALM
    token[ROLE_CLAIM] = user.role
    token[MFA_PENDING_CLAIM] = True
    return token


def blacklist_platform_token(raw_token: str | None) -> None:
    if not raw_token:
        return
    try:
        RefreshToken(raw_token).blacklist()
    except TokenError:
        pass
    except AttributeError:
        logger.warning('Token blacklist app is not installed; token was not retired')
