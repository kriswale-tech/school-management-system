import logging
import secrets

from django.conf import settings
from django.db import transaction

from accounts.helpers import generate_otp
from accounts.models import PhoneOtp, Profile, User

logger = logging.getLogger(__name__)


class OtpVerificationError(Exception):
    pass


def send_signup_otp(phone_number: str) -> None:
    otp = generate_otp()
    PhoneOtp.objects.update_or_create(
        phone_number=phone_number,
        defaults={
            'otp': otp,
            'attempts': 0,
            'is_verified': False,
        },
    )

    if settings.DEBUG:
        print(f"OTP for {phone_number}: {otp}")

    logger.info("OTP issued for %s", phone_number)


def _increment_otp_attempts(phone_otp_id) -> None:
    with transaction.atomic():
        phone_otp = PhoneOtp.objects.select_for_update().get(pk=phone_otp_id)
        phone_otp.attempts += 1
        phone_otp.save(update_fields=['attempts', 'updated_at'])


def verify_signup_otp(phone_number: str, otp: str) -> User:
    phone_otp = PhoneOtp.objects.filter(
        phone_number=phone_number,
        is_verified=False,
    ).first()

    if not phone_otp:
        raise OtpVerificationError('No pending verification for this phone number')

    if phone_otp.attempts >= 3:
        raise OtpVerificationError('Maximum attempts reached')

    if phone_otp.is_expired:
        raise OtpVerificationError('OTP expired')

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
            user.is_active = True
            user.save(update_fields=['is_active', 'updated_at'])

            Profile.objects.get_or_create(user=user)
            return user

    if invalid_otp:
        _increment_otp_attempts(phone_otp_pk)
        raise OtpVerificationError('Invalid OTP')
