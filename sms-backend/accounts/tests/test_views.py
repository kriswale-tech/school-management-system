from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import PhoneOtp, Profile, User
from accounts.tests.base import AccountsAPITestCase
from accounts.tests.factories import PHONE, LOCAL_PHONE, create_phone_otp, create_user, signup_payload


class AdminSignupViewTests(AccountsAPITestCase):
    def setUp(self):
        self.url = reverse('admin-signup')

    def test_signup_sends_otp_and_returns_message(self):
        response = self.client.post(self.url, signup_payload(), format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], 'OTP sent successfully')

        user = User.objects.get(phone_number=PHONE)
        self.assertFalse(user.is_active)
        self.assertTrue(PhoneOtp.objects.filter(phone_number=PHONE).exists())

    def test_signup_rejects_invalid_phone(self):
        response = self.client.post(
            self.url,
            signup_payload(phone_number='12345'),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone_number', response.data)

    def test_signup_rejects_active_duplicate_phone(self):
        create_user(is_active=True)

        response = self.client.post(self.url, signup_payload(), format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone_number', response.data)

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
        self.assertEqual(existing.school.name, 'Updated Academy')


class AdminVerifyOtpViewTests(AccountsAPITestCase):
    def setUp(self):
        self.url = reverse('admin-verify-otp')

    def test_verify_returns_tokens_on_success(self):
        create_user(is_active=False)
        create_phone_otp()

        response = self.client.post(self.url, {
            'phone_number': LOCAL_PHONE,
            'otp': '123456',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'OTP verified successfully')
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

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

        phone_otp = PhoneOtp.objects.get(phone_number=PHONE)
        self.assertEqual(phone_otp.attempts, 1)

    def test_verify_rejects_expired_otp(self):
        create_user(is_active=False)
        phone_otp = create_phone_otp()
        PhoneOtp.objects.filter(pk=phone_otp.pk).update(
            created_at=timezone.now() - timedelta(minutes=6),
        )

        response = self.client.post(self.url, {
            'phone_number': LOCAL_PHONE,
            'otp': '123456',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'OTP expired')


class AdminSignupFlowTests(AccountsAPITestCase):
    def test_full_signup_verify_and_me_flow(self):
        signup_response = self.client.post(
            reverse('admin-signup'),
            signup_payload(),
            format='json',
        )
        self.assertEqual(signup_response.status_code, status.HTTP_201_CREATED)

        otp = PhoneOtp.objects.get(phone_number=PHONE).otp

        verify_response = self.client.post(
            reverse('admin-verify-otp'),
            {'phone_number': LOCAL_PHONE, 'otp': otp},
            format='json',
        )
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)

        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {verify_response.data["access"]}',
        )
        me_response = self.client.get(reverse('me'))

        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data['phone_number'], PHONE)
        self.assertEqual(me_response.data['first_name'], 'Kofi')
        self.assertTrue(me_response.data['is_active'])
        self.assertIsNotNone(me_response.data['profile'])


class MeViewTests(AccountsAPITestCase):
    def setUp(self):
        self.url = reverse('me')
        self.user = create_user(is_active=True)

    def test_me_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_authenticated_user(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phone_number'], PHONE)
        self.assertEqual(response.data['email'], self.user.email)
        self.assertIsNone(response.data['profile'])
