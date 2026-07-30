from datetime import timedelta

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import PhoneOtp, Profile, User
from accounts.tests.base import AccountsAPITestCase
from accounts.tests.factories import (
    LOCAL_PHONE,
    PHONE,
    create_phone_otp,
    create_user,
    set_client_auth_cookies,
    signup_payload,
    user_school,
)


class AdminSignupViewTests(AccountsAPITestCase):
    def setUp(self):
        self.url = reverse('admin-signup')

    def test_signup_sends_otp_and_returns_message(self):
        response = self.client.post(self.url, signup_payload(), format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], 'OTP sent successfully')

        user = User.objects.get(phone_number=PHONE)
        self.assertFalse(user.is_active)
        self.assertTrue(
            PhoneOtp.objects.filter(
                phone_number=PHONE,
                purpose=PhoneOtp.Purpose.SIGNUP,
            ).exists(),
        )

    def test_signup_rejects_invalid_phone(self):
        response = self.client.post(
            self.url,
            signup_payload(phone_number='12345'),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone_number', response.data)

    def test_signup_rejects_duplicate_school_name_for_active_user(self):
        create_user(is_active=True)

        response = self.client.post(
            self.url,
            signup_payload(school_name='Test School'),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup_allows_active_user_to_create_another_school(self):
        create_user(is_active=True)

        response = self.client.post(
            self.url,
            signup_payload(school_name='Second Academy'),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], 'OTP sent successfully')
        self.assertTrue(response.data['linked_existing_account'])
        self.assertEqual(User.objects.filter(phone_number=PHONE).count(), 1)

    def test_signup_allows_inactive_user_to_resubmit(self):
        existing = create_user(is_active=False, first_name='Old')

        response = self.client.post(
            self.url,
            signup_payload(first_name='New', school_name='Updated Academy'),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.filter(phone_number=PHONE).count(), 1)

        existing.refresh_from_db()
        self.assertEqual(existing.first_name, 'New')
        self.assertEqual(user_school(existing).name, 'Updated Academy')


class AdminVerifyOtpViewTests(AccountsAPITestCase):
    def setUp(self):
        self.url = reverse('admin-verify-otp')
        self.access_cookie = settings.SIMPLE_JWT['AUTH_COOKIE']
        self.refresh_cookie = settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH']

    def test_verify_sets_auth_and_csrf_cookies_on_success(self):
        create_user(is_active=False)
        create_phone_otp()

        response = self.client.post(self.url, {
            'phone_number': LOCAL_PHONE,
            'otp': '123456',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'OTP verified successfully')
        self.assertNotIn('access', response.data)
        self.assertNotIn('refresh', response.data)
        self.assertIn(self.access_cookie, response.cookies)
        self.assertIn(self.refresh_cookie, response.cookies)
        self.assertIn('csrftoken', response.cookies)

        user = User.objects.get(phone_number=PHONE)
        self.assertTrue(user.is_active)
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_verify_rejects_wrong_otp(self):
        create_user(is_active=False)
        create_phone_otp()

        response = self.client.post(self.url, {
            'phone_number': LOCAL_PHONE,
            'otp': '000000',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'Invalid OTP')
        self.assertNotIn(self.access_cookie, response.cookies)

        phone_otp = PhoneOtp.objects.get(
            phone_number=PHONE,
            purpose=PhoneOtp.Purpose.SIGNUP,
        )
        self.assertEqual(phone_otp.attempts, 1)

    def test_verify_rejects_expired_otp(self):
        create_user(is_active=False)
        phone_otp = create_phone_otp()
        PhoneOtp.objects.filter(pk=phone_otp.pk).update(
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        response = self.client.post(self.url, {
            'phone_number': LOCAL_PHONE,
            'otp': '123456',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'OTP expired')


class ResendOtpViewTests(AccountsAPITestCase):
    def setUp(self):
        self.url = reverse('resend-otp')

    def test_resend_issues_new_otp_for_inactive_user(self):
        create_user(is_active=False)
        phone_otp = create_phone_otp(otp='000000', attempts=3)
        PhoneOtp.objects.filter(pk=phone_otp.pk).update(
            expires_at=timezone.now() - timedelta(minutes=1),
            sent_at=timezone.now() - timedelta(seconds=61),
        )

        response = self.client.post(self.url, {
            'phone_number': LOCAL_PHONE,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'OTP sent successfully')

        phone_otp.refresh_from_db()
        self.assertNotEqual(phone_otp.otp, '000000')
        self.assertEqual(phone_otp.attempts, 0)
        self.assertFalse(phone_otp.is_expired)

    def test_resend_returns_429_during_cooldown(self):
        create_user(is_active=False)
        create_phone_otp(sent_at=timezone.now())

        response = self.client.post(self.url, {
            'phone_number': LOCAL_PHONE,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('retry_after_seconds', response.data)
        self.assertGreater(response.data['retry_after_seconds'], 0)

    def test_resend_rejects_active_user(self):
        create_user(is_active=True)

        response = self.client.post(self.url, {
            'phone_number': LOCAL_PHONE,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'Phone number already verified')

    def test_resend_rejects_unknown_phone(self):
        response = self.client.post(self.url, {
            'phone_number': LOCAL_PHONE,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'No pending signup for this phone number')

    def test_resend_rejects_invalid_phone(self):
        response = self.client.post(self.url, {
            'phone_number': '12345',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone_number', response.data)

    def test_resend_then_verify_with_new_otp(self):
        create_user(is_active=False)
        create_phone_otp(
            otp='000000',
            sent_at=timezone.now() - timedelta(seconds=61),
        )

        resend_response = self.client.post(self.url, {
            'phone_number': LOCAL_PHONE,
        }, format='json')
        self.assertEqual(resend_response.status_code, status.HTTP_200_OK)

        new_otp = PhoneOtp.objects.get(
            phone_number=PHONE,
            purpose=PhoneOtp.Purpose.SIGNUP,
        ).otp

        verify_response = self.client.post(reverse('admin-verify-otp'), {
            'phone_number': LOCAL_PHONE,
            'otp': new_otp,
        }, format='json')

        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        self.assertTrue(User.objects.get(phone_number=PHONE).is_active)


class AdminSignupFlowTests(AccountsAPITestCase):
    def test_full_signup_verify_and_me_flow(self):
        signup_response = self.client.post(
            reverse('admin-signup'),
            signup_payload(),
            format='json',
        )
        self.assertEqual(signup_response.status_code, status.HTTP_201_CREATED)

        otp = PhoneOtp.objects.get(
            phone_number=PHONE,
            purpose=PhoneOtp.Purpose.SIGNUP,
        ).otp

        verify_response = self.client.post(
            reverse('admin-verify-otp'),
            {'phone_number': LOCAL_PHONE, 'otp': otp},
            format='json',
        )
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)

        me_response = self.client.get(reverse('me'))

        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data['phone_number'], PHONE)
        self.assertEqual(me_response.data['first_name'], 'Kofi')
        self.assertTrue(me_response.data['is_active'])
        self.assertIsNotNone(me_response.data['profile'])


class LoginViewTests(AccountsAPITestCase):
    def setUp(self):
        self.url = reverse('login')
        self.verify_url = reverse('login-verify-otp')
        self.resend_url = reverse('login-resend-otp')
        self.access_cookie = settings.SIMPLE_JWT['AUTH_COOKIE']
        self.refresh_cookie = settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH']

    def test_login_sends_otp_for_active_user(self):
        create_user(is_active=True)

        response = self.client.post(self.url, {
            'phone_number': LOCAL_PHONE,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'OTP sent successfully')
        self.assertTrue(
            PhoneOtp.objects.filter(
                phone_number=PHONE,
                purpose=PhoneOtp.Purpose.LOGIN,
            ).exists(),
        )

    def test_login_rejects_unknown_phone(self):
        response = self.client.post(self.url, {
            'phone_number': LOCAL_PHONE,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'No account found for this phone number')

    def test_login_rejects_inactive_user(self):
        create_user(is_active=False)

        response = self.client.post(self.url, {
            'phone_number': LOCAL_PHONE,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data['message'],
            'Account is not verified. Please complete signup.',
        )

    def test_login_verify_sets_auth_cookies(self):
        create_user(is_active=True)
        create_phone_otp(purpose=PhoneOtp.Purpose.LOGIN)

        response = self.client.post(self.verify_url, {
            'phone_number': LOCAL_PHONE,
            'otp': '123456',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Logged in successfully')
        self.assertIn(self.access_cookie, response.cookies)
        self.assertIn(self.refresh_cookie, response.cookies)
        self.assertIn('csrftoken', response.cookies)

    def test_login_resend_returns_429_during_cooldown(self):
        create_user(is_active=True)
        create_phone_otp(
            purpose=PhoneOtp.Purpose.LOGIN,
            sent_at=timezone.now(),
        )

        response = self.client.post(self.resend_url, {
            'phone_number': LOCAL_PHONE,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('retry_after_seconds', response.data)

    def test_full_login_flow(self):
        create_user(is_active=True)

        login_response = self.client.post(self.url, {
            'phone_number': LOCAL_PHONE,
        }, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        otp = PhoneOtp.objects.get(
            phone_number=PHONE,
            purpose=PhoneOtp.Purpose.LOGIN,
        ).otp

        verify_response = self.client.post(self.verify_url, {
            'phone_number': LOCAL_PHONE,
            'otp': otp,
        }, format='json')
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)

        me_response = self.client.get(reverse('me'))
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data['phone_number'], PHONE)


class MeViewTests(AccountsAPITestCase):
    def setUp(self):
        self.url = reverse('me')
        self.user = create_user(is_active=True)

    def test_me_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_authenticated_user_with_cookie(self):
        set_client_auth_cookies(self.client, self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phone_number'], PHONE)
        self.assertEqual(response.data['email'], self.user.email)
        self.assertIsNone(response.data['profile'])


class RefreshTokenViewTests(AccountsAPITestCase):
    def setUp(self):
        self.url = reverse('refresh-token')
        self.user = create_user(is_active=True)
        self.access_cookie = settings.SIMPLE_JWT['AUTH_COOKIE']
        self.refresh_cookie = settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH']

    def test_refresh_requires_refresh_cookie(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['message'], 'Refresh token missing')

    def test_refresh_issues_new_access_cookie(self):
        set_client_auth_cookies(self.client, self.user)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Token refreshed')
        self.assertIn(self.access_cookie, response.cookies)
        self.assertIn(self.refresh_cookie, response.cookies)
        self.assertIn('csrftoken', response.cookies)

        me_response = self.client.get(reverse('me'))
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)


class LogoutViewTests(AccountsAPITestCase):
    def setUp(self):
        self.url = reverse('logout')
        self.user = create_user(is_active=True)
        self.access_cookie = settings.SIMPLE_JWT['AUTH_COOKIE']
        self.refresh_cookie = settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH']

    def test_logout_clears_auth_cookies(self):
        refresh = set_client_auth_cookies(self.client, self.user)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Logged out')
        self.assertEqual(response.cookies[self.access_cookie]['max-age'], 0)
        self.assertEqual(response.cookies[self.refresh_cookie]['max-age'], 0)

        me_response = self.client.get(reverse('me'))
        self.assertEqual(me_response.status_code, status.HTTP_401_UNAUTHORIZED)

        with self.assertRaises(TokenError):
            RefreshToken(str(refresh))

    def test_logout_clears_cookies_when_access_token_is_invalid(self):
        refresh = set_client_auth_cookies(self.client, self.user)
        self.client.cookies[settings.SIMPLE_JWT['AUTH_COOKIE']] = 'invalid-access-token'

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.cookies[self.access_cookie]['max-age'], 0)
        self.assertEqual(response.cookies[self.refresh_cookie]['max-age'], 0)

        with self.assertRaises(TokenError):
            RefreshToken(str(refresh))

    def test_logout_clears_cookies_without_access_token(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.cookies[settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH']] = str(refresh)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.cookies[self.access_cookie]['max-age'], 0)
        self.assertEqual(response.cookies[self.refresh_cookie]['max-age'], 0)
