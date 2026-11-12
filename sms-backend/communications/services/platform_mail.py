"""Email platform operators who can open Messages.

Recipients are active platform users with a Messages role: super admin,
finance, operations, and support. Curriculum admins are not included.
The address is the email they sign in with.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail

from platform_admin.models import PlatformUser

logger = logging.getLogger(__name__)

MESSAGE_ADMIN_ROLES = (
    PlatformUser.Role.SUPER_ADMIN,
    PlatformUser.Role.FINANCE,
    PlatformUser.Role.OPERATIONS,
    PlatformUser.Role.SUPPORT,
)


def messaging_admin_emails() -> list[str]:
    """Sign-in emails for platform admins who can open Messages."""
    emails = (
        PlatformUser.objects.filter(is_active=True, role__in=MESSAGE_ADMIN_ROLES)
        .exclude(email='')
        .order_by('email')
        .values_list('email', flat=True)
    )
    seen: list[str] = []
    for email in emails:
        cleaned = (email or '').strip()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return seen


def send_platform_email(*, subject: str, body: str) -> int:
    """Send one plain-text email. Returns how many messages Django accepted."""
    recipients = messaging_admin_emails()
    if not recipients:
        logger.warning('No platform admin email for: %s', subject)
        return 0
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'noreply@localhost'
    try:
        return send_mail(subject, body, from_email, recipients, fail_silently=True)
    except Exception:
        logger.exception('Platform email failed: %s', subject)
        return 0
