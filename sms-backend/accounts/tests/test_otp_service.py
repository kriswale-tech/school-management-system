from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from accounts.models import PhoneOtp, Profile
from accounts.services.otp import (
    OtpResendCooldownError,
    OtpResendError,
    OtpSendError,
    OtpVerificationError,
    resend_login_otp,
    resend_signup_otp,
    send_login_otp,
    send_signup_otp,
    verify_login_otp,
    verify_signup_otp,
)
from accounts.tests.factories import PHONE, OTP, create_phone_otp, create_user


class SendSignupOtpTests(TestCase):
    def test_creates_phone_otp_record(self):
        send_signup_otp(PHONE)

        phone_otp = PhoneOtp.objects.get(
            phone_number=PHONE,
            purpose=PhoneOtp.Purpose.SIGNUP,
        )
        self.assertEqual(len(phone_otp.otp), 6)
        self.assertFalse(phone_otp.is_verified)
        self.assertEqual(phone_otp.attempts, 0)

    def test_resend_resets_attempts_verification_and_expiry(self):
        PhoneOtp.objects.create(
            phone_number=PHONE,
            purpose=PhoneOtp.Purpose.SIGNUP,
            otp='000000',
            attempts=2,
            is_verified=True,
            expires_at=timezone.now() - timedelta(minutes=1),
            sent_at=timezone.now() - timedelta(seconds=61),
        )

        send_signup_otp(PHONE)

        phone_otp = PhoneOtp.objects.get(
            phone_number=PHONE,
            purpose=PhoneOtp.Purpose.SIGNUP,
        )
        self.assertEqual(phone_otp.attempts, 0)
        self.assertFalse(phone_otp.is_verified)
        self.assertNotEqual(phone_otp.otp, '000000')
        self.assertFalse(phone_otp.is_expired)
        self.assertGreater(phone_otp.expires_at, timezone.now())


class ResendSignupOtpTests(TestCase):
    def test_resend_issues_new_otp_for_inactive_user(self):
        create_user(is_active=False)
        PhoneOtp.objects.create(
            phone_number=PHONE,
            purpose=PhoneOtp.Purpose.SIGNUP,
            otp='000000',
            attempts=3,
            expires_at=timezone.now() - timedelta(minutes=1),
            sent_at=timezone.now() - timedelta(seconds=61),
        )

        resend_signup_otp(PHONE)

        phone_otp = PhoneOtp.objects.get(
            phone_number=PHONE,
            purpose=PhoneOtp.Purpose.SIGNUP,
        )
        self.assertNotEqual(phone_otp.otp, '000000')
        self.assertEqual(phone_otp.attempts, 0)
        self.assertFalse(phone_otp.is_expired)

    def test_resend_invalidates_previous_otp(self):
        create_user(is_active=False)
        PhoneOtp.objects.create(
            phone_number=PHONE,
            purpose=PhoneOtp.Purpose.SIGNUP,
            otp='111111',
            expires_at=PhoneOtp.default_expires_at(),
            sent_at=timezone.now() - timedelta(seconds=61),
        )

        resend_signup_otp(PHONE)

        with self.assertRaisesMessage(OtpVerificationError, 'Invalid OTP'):
            verify_signup_otp(PHONE, '111111')

    def test_resend_enforces_cooldown(self):
        create_user(is_active=False)
        PhoneOtp.objects.create(
            phone_number=PHONE,
            purpose=PhoneOtp.Purpose.SIGNUP,
            otp='123456',
            expires_at=PhoneOtp.default_expires_at(),
            sent_at=timezone.now(),
        )

        with self.assertRaises(OtpResendCooldownError) as ctx:
            resend_signup_otp(PHONE)

        self.assertGreater(ctx.exception.retry_after_seconds, 0)
        self.assertLessEqual(ctx.exception.retry_after_seconds, 60)

    def test_resend_rejects_active_user_without_pending_school(self):
        from django.core.cache import cache

        cache.clear()
        create_user(is_active=True)

        with self.assertRaisesMessage(OtpResendError, 'Phone number already verified'):
            resend_signup_otp(PHONE)

    def test_resend_allows_active_user_with_pending_school(self):
        from accounts.services.registration import stage_pending_school

        create_user(is_active=True)
        stage_pending_school(PHONE, 'Second Academy')

        resend_signup_otp(PHONE)

        self.assertTrue(
            PhoneOtp.objects.filter(
                phone_number=PHONE,
                purpose=PhoneOtp.Purpose.SIGNUP,
            ).exists(),
        )

    def test_resend_rejects_unknown_phone(self):
        with self.assertRaisesMessage(OtpResendError, 'No pending signup for this phone number'):
            resend_signup_otp(PHONE)


class VerifySignupOtpTests(TestCase):
    def setUp(self):
        self.user = create_user(is_active=False)
        self.phone_otp = create_phone_otp()

    def test_valid_otp_activates_user_and_creates_profile(self):
        result = verify_signup_otp(PHONE, OTP)
        user = result.user

        user.refresh_from_db()
        self.phone_otp.refresh_from_db()

        self.assertTrue(user.is_active)
        self.assertFalse(result.linked_existing_account)
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
            expires_at=timezone.now() - timedelta(minutes=1),
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


class SendLoginOtpTests(TestCase):
    def test_creates_login_otp_for_active_user(self):
        create_user(is_active=True)

        send_login_otp(PHONE)

        phone_otp = PhoneOtp.objects.get(
            phone_number=PHONE,
            purpose=PhoneOtp.Purpose.LOGIN,
        )
        self.assertEqual(len(phone_otp.otp), 6)
        self.assertFalse(phone_otp.is_verified)

    def test_rejects_unknown_phone(self):
        with self.assertRaisesMessage(OtpSendError, 'No account found for this phone number'):
            send_login_otp(PHONE)

    def test_rejects_inactive_user(self):
        create_user(is_active=False)

        with self.assertRaisesMessage(
            OtpSendError,
            'Account is not verified. Please complete signup.',
        ):
            send_login_otp(PHONE)


class ResendLoginOtpTests(TestCase):
    def test_resend_issues_new_login_otp_for_active_user(self):
        create_user(is_active=True)
        PhoneOtp.objects.create(
            phone_number=PHONE,
            purpose=PhoneOtp.Purpose.LOGIN,
            otp='000000',
            attempts=3,
            expires_at=timezone.now() - timedelta(minutes=1),
            sent_at=timezone.now() - timedelta(seconds=61),
        )

        resend_login_otp(PHONE)

        phone_otp = PhoneOtp.objects.get(
            phone_number=PHONE,
            purpose=PhoneOtp.Purpose.LOGIN,
        )
        self.assertNotEqual(phone_otp.otp, '000000')
        self.assertEqual(phone_otp.attempts, 0)

    def test_login_resend_not_blocked_by_signup_otp_cooldown(self):
        create_user(is_active=True)
        now = timezone.now()
        PhoneOtp.objects.create(
            phone_number=PHONE,
            purpose=PhoneOtp.Purpose.SIGNUP,
            otp='111111',
            expires_at=PhoneOtp.default_expires_at(),
            sent_at=now,
        )
        PhoneOtp.objects.create(
            phone_number=PHONE,
            purpose=PhoneOtp.Purpose.LOGIN,
            otp='222222',
            expires_at=PhoneOtp.default_expires_at(),
            sent_at=now - timedelta(seconds=61),
        )

        resend_login_otp(PHONE)

        phone_otp = PhoneOtp.objects.get(
            phone_number=PHONE,
            purpose=PhoneOtp.Purpose.LOGIN,
        )
        self.assertNotEqual(phone_otp.otp, '222222')


class VerifyLoginOtpTests(TestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        self.phone_otp = create_phone_otp(purpose=PhoneOtp.Purpose.LOGIN)

    def test_valid_otp_returns_active_user_without_changing_activation(self):
        user = verify_login_otp(PHONE, OTP)

        user.refresh_from_db()
        self.phone_otp.refresh_from_db()

        self.assertTrue(user.is_active)
        self.assertTrue(self.phone_otp.is_verified)

    def test_wrong_otp_increments_attempts(self):
        with self.assertRaisesMessage(OtpVerificationError, 'Invalid OTP'):
            verify_login_otp(PHONE, '000000')

        self.phone_otp.refresh_from_db()
        self.assertEqual(self.phone_otp.attempts, 1)

    def test_signup_otp_cannot_be_used_for_login(self):
        create_phone_otp(purpose=PhoneOtp.Purpose.SIGNUP, otp='654321')

        with self.assertRaisesMessage(OtpVerificationError, 'Invalid OTP'):
            verify_login_otp(PHONE, '654321')
