import pyotp
from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from platform_admin.models import PlatformAuditLog, PlatformUser
from platform_admin.services.settings import clear_platform_settings_cache, get_platform_settings


class PlatformAuthTests(APITestCase):
    def setUp(self):
        clear_platform_settings_cache()
        self.user = PlatformUser.objects.create_user(
            email='ops@schoolasst.test',
            password='SecurePass123!',
            first_name='Ops',
            last_name='Admin',
            role=PlatformUser.Role.SUPER_ADMIN,
        )
        self.access_cookie = settings.PLATFORM_JWT['AUTH_COOKIE']
        self.refresh_cookie = settings.PLATFORM_JWT['AUTH_COOKIE_REFRESH']

    def test_hello_unauthenticated(self):
        response = self.client.get(reverse('platform-hello'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['authenticated'])

    def test_login_sets_platform_cookies(self):
        response = self.client.post(
            reverse('platform-login'),
            {'email': 'ops@schoolasst.test', 'password': 'SecurePass123!'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['mfa_required'])
        self.assertIn(self.access_cookie, response.cookies)
        self.assertIn(self.refresh_cookie, response.cookies)
        self.assertTrue(
            PlatformAuditLog.objects.filter(action='platform.auth.login_password').exists(),
        )

    def test_login_rejects_bad_password(self):
        response = self.client.post(
            reverse('platform-login'),
            {'email': 'ops@schoolasst.test', 'password': 'wrong'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_platform_auth(self):
        denied = self.client.get(reverse('platform-me'))
        self.assertIn(
            denied.status_code,
            {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN},
        )

        login = self.client.post(
            reverse('platform-login'),
            {'email': 'ops@schoolasst.test', 'password': 'SecurePass123!'},
            format='json',
        )
        self.client.cookies[self.access_cookie] = login.cookies[self.access_cookie].value
        me = self.client.get(reverse('platform-me'))
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data['email'], 'ops@schoolasst.test')

    def test_mfa_login_flow(self):
        secret = pyotp.random_base32()
        self.user.mfa_secret = secret
        self.user.mfa_enabled = True
        self.user.save(update_fields=['mfa_secret', 'mfa_enabled', 'updated_at'])

        challenge = self.client.post(
            reverse('platform-login'),
            {'email': 'ops@schoolasst.test', 'password': 'SecurePass123!'},
            format='json',
        )
        self.assertTrue(challenge.data['mfa_required'])
        self.assertIn('mfa_token', challenge.data)
        self.assertNotIn(self.access_cookie, challenge.cookies)

        code = pyotp.TOTP(secret).now()
        verified = self.client.post(
            reverse('platform-mfa-verify'),
            {'code': code, 'mfa_token': challenge.data['mfa_token']},
            format='json',
            HTTP_AUTHORIZATION=f"Bearer {challenge.data['mfa_token']}",
        )
        self.assertEqual(verified.status_code, status.HTTP_200_OK)
        self.assertIn(self.access_cookie, verified.cookies)

    def test_settings_get_and_patch(self):
        settings_row = get_platform_settings()
        self.assertTrue(settings_row.public_school_registration_enabled)

        login = self.client.post(
            reverse('platform-login'),
            {'email': 'ops@schoolasst.test', 'password': 'SecurePass123!'},
            format='json',
        )
        self.client.cookies[self.access_cookie] = login.cookies[self.access_cookie].value

        patched = self.client.patch(
            reverse('platform-settings'),
            {
                'public_school_registration_enabled': False,
                'subscription_grace_days': 10,
            },
            format='json',
        )
        self.assertEqual(patched.status_code, status.HTTP_200_OK)
        self.assertFalse(patched.data['public_school_registration_enabled'])
        self.assertEqual(patched.data['subscription_grace_days'], 10)
