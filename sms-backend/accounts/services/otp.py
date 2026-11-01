import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from accounts.helpers import generate_otp
from accounts.models import PhoneOtp, Profile, SchoolMembership, User
from notifications.services.email_context import default_app_logo_url
from shared.services.arkesel_sms import send_sms

logger = logging.getLogger(__name__)


class OtpVerificationError(Exception):
    pass


class OtpSendError(Exception):
    pass


class OtpResendError(Exception):
    pass


class OtpResendCooldownError(OtpResendError):
    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            f'Please wait {retry_after_seconds} seconds before requesting a new OTP'
        )


def _otp_expires_at():
    return timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)


def _store_otp(phone_number: str, purpose: str) -> str:
    now = timezone.now()
    otp = generate_otp()
    PhoneOtp.objects.update_or_create(
        phone_number=phone_number,
        purpose=purpose,
        defaults={
            'otp': otp,
            'attempts': 0,
            'is_verified': False,
            'expires_at': _otp_expires_at(),
            'sent_at': now,
        },
    )
    return otp


def send_otp(phone_number: str, purpose: str) -> None:
    """Store an OTP. Signup keeps DEBUG console print; login uses deliver path."""
    otp = _store_otp(phone_number, purpose)

    if purpose == PhoneOtp.Purpose.SIGNUP and settings.DEBUG:
        print(f'OTP ({purpose}) for {phone_number}: {otp}')

    logger.info('OTP issued for %s (%s)', phone_number, purpose)


def _arkesel_message_id(payload: dict | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    if payload.get('message_id'):
        return str(payload['message_id'])
    data = payload.get('data')
    if isinstance(data, list) and data and isinstance(data[0], dict):
        for key in ('id', 'message_id', 'sms_id'):
            if data[0].get(key):
                return str(data[0][key])
    if isinstance(data, dict):
        for key in ('id', 'message_id', 'sms_id'):
            if data.get(key):
                return str(data[key])
    return None


def _send_login_otp_sms(phone_number: str, otp: str) -> dict | None:
    """Send login OTP by SMS. Returns Arkesel payload on success, else None."""
    sender = getattr(settings, 'ARKESEL_SMS_SENDER', None) or 'SCHOOLASST'
    message = (
        f'Your {sender} login code is {otp}. '
        f'It expires in {settings.OTP_EXPIRY_MINUTES} minutes.'
    )
    try:
        return send_sms(phone_number, message)
    except Exception:
        logger.exception('Failed to send login OTP SMS to %s', phone_number)
        return None


def _send_login_otp_email(user: User, otp: str) -> None:
    email = (user.email or '').strip()
    if not email:
        return

    name = (user.get_full_name() or '').strip()
    context = {
        'otp': otp,
        'expiry_minutes': settings.OTP_EXPIRY_MINUTES,
        'greeting': f'Hi {name},' if name else '',
        'app_logo_url': default_app_logo_url(),
        'preheader': f'Your login code is {otp}',
    }
    try:
        text_body = render_to_string('accounts/email/login_otp.txt', context)
        html_body = render_to_string('accounts/email/login_otp.html', context)
        message = EmailMultiAlternatives(
            subject='Your login code',
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        message.attach_alternative(html_body, 'text/html')
        message.send(fail_silently=False)
    except Exception:
        logger.exception('Failed to send login OTP email to %s', email)


def _deliver_login_otp(user: User, otp: str) -> None:
    """SMS primary; email if present; DEBUG console for success or SMS failure."""
    sms_result = _send_login_otp_sms(user.phone_number, otp)
    _send_login_otp_email(user, otp)

    if not settings.DEBUG:
        return

    if sms_result is not None:
        message_id = _arkesel_message_id(sms_result)
        status = sms_result.get('status') if isinstance(sms_result, dict) else None
        parts = [f'Login OTP SMS OK for {user.phone_number}']
        if status:
            parts.append(f'status={status}')
        if message_id:
            parts.append(f'id={message_id}')
        parts.append(f'OTP={otp}')
        print(' | '.join(parts))
        return

    print(f'OTP (login) for {user.phone_number}: {otp}')
    logger.warning(
        'Login OTP SMS failed for %s; printed to console (DEBUG)',
        user.phone_number,
    )


def _check_resend_cooldown(phone_number: str, purpose: str) -> None:
    phone_otp = PhoneOtp.objects.filter(
        phone_number=phone_number,
        purpose=purpose,
    ).first()
    if not phone_otp:
        return

    elapsed = (timezone.now() - phone_otp.sent_at).total_seconds()
    remaining = settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed
    if remaining > 0:
        raise OtpResendCooldownError(int(remaining))


def _validate_resend(phone_number: str, purpose: str) -> None:
    from accounts.services.registration import get_pending_school

    user = User.objects.filter(phone_number=phone_number).first()

    if purpose == PhoneOtp.Purpose.SIGNUP:
        if not user:
            raise OtpResendError('No pending signup for this phone number')
        # Returning users may also be creating a school via signup; they keep a
        # staged school name until OTP succeeds.
        if user.is_active and get_pending_school(phone_number) is None:
            raise OtpResendError('Phone number already verified')
        return

    if not user:
        raise OtpResendError('No account found for this phone number')
    if not user.is_active:
        raise OtpResendError('Account is not verified. Please complete signup.')


def resend_otp(phone_number: str, purpose: str) -> None:
    _validate_resend(phone_number, purpose)
    _check_resend_cooldown(phone_number, purpose)
    send_otp(phone_number, purpose)


def send_signup_otp(phone_number: str) -> None:
    send_otp(phone_number, PhoneOtp.Purpose.SIGNUP)


def resend_signup_otp(phone_number: str) -> None:
    resend_otp(phone_number, PhoneOtp.Purpose.SIGNUP)


def send_login_otp(phone_number: str) -> None:
    user = User.objects.filter(phone_number=phone_number).first()
    if not user:
        raise OtpSendError('No account found for this phone number')
    if not user.is_active:
        raise OtpSendError('Account is not verified. Please complete signup.')

    otp = _store_otp(phone_number, PhoneOtp.Purpose.LOGIN)
    logger.info('OTP issued for %s (%s)', phone_number, PhoneOtp.Purpose.LOGIN)
    _deliver_login_otp(user, otp)


def resend_login_otp(phone_number: str) -> None:
    _validate_resend(phone_number, PhoneOtp.Purpose.LOGIN)
    _check_resend_cooldown(phone_number, PhoneOtp.Purpose.LOGIN)
    send_login_otp(phone_number)


def _increment_otp_attempts(phone_otp_id) -> None:
    with transaction.atomic():
        phone_otp = PhoneOtp.objects.select_for_update().get(pk=phone_otp_id)
        phone_otp.attempts += 1
        phone_otp.save(update_fields=['attempts', 'updated_at'])


def verify_otp(phone_number: str, otp: str, purpose: str) -> User:
    phone_otp = PhoneOtp.objects.filter(
        phone_number=phone_number,
        purpose=purpose,
        is_verified=False,
    ).first()

    if not phone_otp:
        raise OtpVerificationError('No pending verification for this phone number')

    if phone_otp.attempts >= 3:
        raise OtpVerificationError('Maximum attempts reached')

    if phone_otp.is_expired:
        raise OtpVerificationError('OTP expired')

    user = User.objects.filter(phone_number=phone_number).first()
    if not user:
        raise OtpVerificationError('No pending verification for this phone number')

    if purpose == PhoneOtp.Purpose.LOGIN and not user.is_active:
        raise OtpVerificationError('Account is not verified. Please complete signup.')

    invalid_otp = False
    phone_otp_pk = phone_otp.pk

    with transaction.atomic():
        phone_otp = PhoneOtp.objects.select_for_update().get(pk=phone_otp_pk)

        if phone_otp.is_verified:
            raise OtpVerificationError('No pending verification for this phone number')
        if phone_otp.attempts >= 3:
            raise OtpVerificationError('Maximum attempts reached')
        if phone_otp.is_expired:
            raise OtpVerificationError('OTP expired')

        if not secrets.compare_digest(phone_otp.otp, otp):
            invalid_otp = True
        else:
            phone_otp.is_verified = True
            phone_otp.save(update_fields=['is_verified', 'updated_at'])

            user = User.objects.select_for_update().get(phone_number=phone_number)

            if purpose == PhoneOtp.Purpose.SIGNUP and not user.is_active:
                user.is_active = True
                user.save(update_fields=['is_active', 'updated_at'])
                Profile.objects.get_or_create(user=user)
                # Verifying the phone confirms the school access granted at signup.
                SchoolMembership.objects.filter(user=user, is_active=False).update(
                    is_active=True,
                )

            return user

    if invalid_otp:
        _increment_otp_attempts(phone_otp_pk)
        raise OtpVerificationError('Invalid OTP')


def verify_signup_otp(phone_number: str, otp: str):
    """Verify signup OTP. Returning users also get their staged school created."""
    from accounts.services.registration import (
        CompleteSignupResult,
        complete_pending_school_creation,
    )

    existing = User.objects.filter(phone_number=phone_number).first()
    was_active = bool(existing and existing.is_active)

    user = verify_otp(phone_number, otp, PhoneOtp.Purpose.SIGNUP)
    membership = complete_pending_school_creation(user)

    if was_active:
        if membership is None:
            raise OtpVerificationError(
                'Your school creation request expired. Please start signup again.',
            )
        return CompleteSignupResult(
            user=user,
            membership=membership,
            linked_existing_account=True,
        )

    return CompleteSignupResult(
        user=user,
        membership=membership,
        linked_existing_account=False,
    )


def verify_login_otp(phone_number: str, otp: str) -> User:
    return verify_otp(phone_number, otp, PhoneOtp.Purpose.LOGIN)
