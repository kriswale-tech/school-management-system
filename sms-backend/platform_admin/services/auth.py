from __future__ import annotations

import pyotp
from django.conf import settings
from django.contrib.auth.hashers import check_password
from rest_framework.exceptions import AuthenticationFailed, ValidationError

from platform_admin.models import PlatformUser
from platform_admin.services.audit import record_audit
from platform_admin.tokens import (
    build_mfa_pending_token,
    build_platform_token,
)


def authenticate_platform_password(email: str, password: str) -> PlatformUser:
    normalized = email.strip().lower()
    try:
        user = PlatformUser.objects.get(email__iexact=normalized)
    except PlatformUser.DoesNotExist as exc:
        raise AuthenticationFailed('Invalid email or password.') from exc

    if not user.is_active:
        raise AuthenticationFailed('This account is inactive.')

    if not check_password(password, user.password):
        raise AuthenticationFailed('Invalid email or password.')

    return user


def begin_login(user: PlatformUser) -> dict:
    """Return either full tokens or an MFA challenge payload."""
    if user.mfa_enabled and user.mfa_secret:
        pending = build_mfa_pending_token(user)
        return {
            'mfa_required': True,
            'mfa_token': str(pending),
            'user': user,
        }

    refresh = build_platform_token(user)
    return {
        'mfa_required': False,
        'refresh': refresh,
        'access': refresh.access_token,
        'user': user,
    }


def verify_login_mfa(user: PlatformUser, code: str) -> dict:
    if not user.mfa_enabled or not user.mfa_secret:
        raise ValidationError({'detail': 'MFA is not enabled for this account.'})

    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(code.strip(), valid_window=1):
        raise AuthenticationFailed('Invalid MFA code.')

    refresh = build_platform_token(user)
    return {
        'refresh': refresh,
        'access': refresh.access_token,
        'user': user,
    }


def provision_mfa_secret(user: PlatformUser) -> dict:
    secret = pyotp.random_base32()
    user.mfa_secret = secret
    user.mfa_enabled = False
    user.save(update_fields=['mfa_secret', 'mfa_enabled', 'updated_at'])
    issuer = settings.PLATFORM_MFA_ISSUER
    uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=issuer)
    return {'secret': secret, 'otpauth_uri': uri}


def confirm_mfa_setup(user: PlatformUser, code: str) -> PlatformUser:
    if not user.mfa_secret:
        raise ValidationError({'detail': 'Start MFA setup before confirming.'})
    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(code.strip(), valid_window=1):
        raise ValidationError({'code': 'Invalid MFA code.'})
    user.mfa_enabled = True
    user.save(update_fields=['mfa_enabled', 'updated_at'])
    record_audit(
        actor=user,
        action='platform.mfa.enabled',
        target_type='platform_user',
        target_id=str(user.pk),
    )
    return user


def disable_mfa(user: PlatformUser, code: str) -> PlatformUser:
    if not user.mfa_enabled or not user.mfa_secret:
        raise ValidationError({'detail': 'MFA is not enabled.'})
    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(code.strip(), valid_window=1):
        raise ValidationError({'code': 'Invalid MFA code.'})
    user.mfa_enabled = False
    user.mfa_secret = ''
    user.save(update_fields=['mfa_enabled', 'mfa_secret', 'updated_at'])
    record_audit(
        actor=user,
        action='platform.mfa.disabled',
        target_type='platform_user',
        target_id=str(user.pk),
    )
    return user
