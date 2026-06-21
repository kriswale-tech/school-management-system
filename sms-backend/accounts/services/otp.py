import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.helpers import generate_otp
from accounts.models import PhoneOtp, Profile, User

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


def send_otp(phone_number: str, purpose: str) -> None:
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

    if settings.DEBUG:
        print(f"OTP ({purpose}) for {phone_number}: {otp}")

    logger.info("OTP issued for %s (%s)", phone_number, purpose)


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
    user = User.objects.filter(phone_number=phone_number).first()

    if purpose == PhoneOtp.Purpose.SIGNUP:
        if not user:
            raise OtpResendError('No pending signup for this phone number')
        if user.is_active:
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
    send_otp(phone_number, PhoneOtp.Purpose.LOGIN)


def resend_login_otp(phone_number: str) -> None:
    resend_otp(phone_number, PhoneOtp.Purpose.LOGIN)


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

            if purpose == PhoneOtp.Purpose.SIGNUP:
                user.is_active = True
                user.save(update_fields=['is_active', 'updated_at'])
                Profile.objects.get_or_create(user=user)

            return user

    if invalid_otp:
        _increment_otp_attempts(phone_otp_pk)
        raise OtpVerificationError('Invalid OTP')


def verify_signup_otp(phone_number: str, otp: str) -> User:
    return verify_otp(phone_number, otp, PhoneOtp.Purpose.SIGNUP)


def verify_login_otp(phone_number: str, otp: str) -> User:
    return verify_otp(phone_number, otp, PhoneOtp.Purpose.LOGIN)
