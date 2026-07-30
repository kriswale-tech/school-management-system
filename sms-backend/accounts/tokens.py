import logging

from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import SchoolMembership, User

logger = logging.getLogger(__name__)

SCHOOL_CLAIM = 'school_id'
ROLE_CLAIM = 'role'
MEMBERSHIP_CLAIM = 'membership_id'


def build_token(user: User, membership: SchoolMembership | None = None) -> RefreshToken:
    """Issue a refresh token, scoped to a school when a membership is given.

    simplejwt copies non-reserved claims from the refresh token onto every
    access token derived from it, so the scope survives token refresh.
    """
    refresh = RefreshToken.for_user(user)

    if membership is not None:
        refresh[SCHOOL_CLAIM] = str(membership.school_id)
        refresh[ROLE_CLAIM] = membership.role
        refresh[MEMBERSHIP_CLAIM] = str(membership.pk)

    return refresh


def token_school_id(token) -> str | None:
    return token.get(SCHOOL_CLAIM)


def blacklist_token(raw_token: str | None) -> None:
    """Retire a refresh token. Missing or already-invalid tokens are ignored."""
    if not raw_token:
        return

    try:
        RefreshToken(raw_token).blacklist()
    except TokenError:
        pass
    except AttributeError:
        logger.warning('Token blacklist app is not installed; token was not retired')
