from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from platform_admin.models import PlatformAuditLog, PlatformUser


def _login(client: APIClient, email: str, role: str) -> None:
    PlatformUser.objects.create_user(
        email=email,
        password='SecurePass123!',
        role=role,
    )
    login = client.post(
        reverse('platform-login'),
        {'email': email, 'password': 'SecurePass123!'},
        format='json',
    )
    access = settings.PLATFORM_JWT['AUTH_COOKIE']
    client.cookies[access] = login.cookies[access].value


@override_settings(ARKESEL_API_KEY='test-key', ARKESEL_SANDBOX=True, ARKESEL_SMS_SENDER='SCHOOL')
class ArkeselTestSendTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        _login(self.client, 'sms-test@example.com', PlatformUser.Role.SUPER_ADMIN)
        self.url = reverse('platform-messages-arkesel-test-send')

    @patch('communications.views.messages.send_sms')
    def test_super_admin_sends_through_the_app_path(self, mock_send):
        mock_send.return_value = {
            'status': 'success',
            'data': [{'id': 'sms-1', 'recipient': '+233244000000'}],
        }

        response = self.client.post(
            self.url,
            {'to': '0244000000', 'message': 'Hello from platform admin'},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['to'], '+233244000000')
        self.assertTrue(response.data['sandbox'])
        self.assertEqual(response.data['provider_message_id'], 'sms-1')
        mock_send.assert_called_once_with('+233244000000', 'Hello from platform admin')
        self.assertTrue(
            PlatformAuditLog.objects.filter(
                action='messages.arkesel_test.sent',
                target_id='sms-1',
            ).exists(),
        )

    def test_rejects_a_bad_phone_number(self):
        response = self.client.post(
            self.url,
            {'to': '123', 'message': 'Hello'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid phone number', str(response.data))

    def test_support_cannot_send(self):
        client = APIClient()
        _login(client, 'sms-support@example.com', PlatformUser.Role.SUPPORT)
        response = client.post(
            self.url,
            {'to': '0244000000', 'message': 'Hello'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)
