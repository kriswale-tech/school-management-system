from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from accounts.models import PhoneOtp, Profile
from accounts.services.otp import OtpVerificationError, send_signup_otp, verify_signup_otp
from accounts.tests.factories import PHONE, OTP, create_phone_otp, create_user


class SendSignupOtpTests(TestCase):
    def test_creates_phone_otp_record(self):
        send_signup_otp(PHONE)

        phone_otp = PhoneOtp.objects.get(phone_number=PHONE)
        self.assertEqual(len(phone_otp.otp), 6)
        self.assertFalse(phone_otp.is_verified)
        self.assertEqual(phone_otp.attempts, 0)

    def test_resend_resets_attempts_and_verification(self):
        PhoneOtp.objects.create(
            phone_number=PHONE,
            otp='000000',
            attempts=2,
            is_verified=True,
        )

        send_signup_otp(PHONE)

        phone_otp = PhoneOtp.objects.get(phone_number=PHONE)
        self.assertEqual(phone_otp.attempts, 0)
        self.assertFalse(phone_otp.is_verified)
        self.assertNotEqual(phone_otp.otp, '000000')


class VerifySignupOtpTests(TestCase):
    def setUp(self):
        self.user = create_user(is_active=False)
        self.phone_otp = create_phone_otp()

    def test_valid_otp_activates_user_and_creates_profile(self):
        user = verify_signup_otp(PHONE, OTP)

        user.refresh_from_db()
        self.phone_otp.refresh_from_db()

        self.assertTrue(user.is_active)
        self.assertTrue(self.phone_otp.is_verified)
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_wrong_otp_increments_attempts(self):
        with self.assertRaisesMessage(OtpVerificationError, 'Invalid OTP'):
            verify_signup_otp(PHONE, '000000')

        self.phone_otp.refresh_from_db()
        self.user.refresh_from_db()

        self.assertEqual(self.phone_otp.attempts, 1)
        self.assertFalse(self.user.is_active)

    def test_max_attempts_blocks_verification(self):
        self.phone_otp.attempts = 3
        self.phone_otp.save()

        with self.assertRaisesMessage(OtpVerificationError, 'Maximum attempts reached'):
            verify_signup_otp(PHONE, OTP)

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_expired_otp_is_rejected(self):
        PhoneOtp.objects.filter(pk=self.phone_otp.pk).update(
            created_at=timezone.now() - timedelta(minutes=6),
        )
        self.phone_otp.refresh_from_db()

        with self.assertRaisesMessage(OtpVerificationError, 'OTP expired'):
            verify_signup_otp(PHONE, OTP)

    def test_no_pending_otp_raises_error(self):
        self.phone_otp.is_verified = True
        self.phone_otp.save()

        with self.assertRaisesMessage(
            OtpVerificationError,
            'No pending verification for this phone number',
        ):
            verify_signup_otp(PHONE, OTP)

    def test_missing_otp_record_raises_error(self):
        self.phone_otp.delete()

        with self.assertRaisesMessage(
            OtpVerificationError,
            'No pending verification for this phone number',
        ):
            verify_signup_otp(PHONE, OTP)

    @patch('accounts.services.otp.secrets.compare_digest', return_value=False)
    def test_uses_constant_time_comparison(self, mock_compare):
        with self.assertRaisesMessage(OtpVerificationError, 'Invalid OTP'):
            verify_signup_otp(PHONE, OTP)

        mock_compare.assert_called_once_with(OTP, OTP)
