from unittest.mock import patch

from django.conf import settings
from django.test import TestCase
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


class SesTestSendAuditTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        _login(self.client, 'ses-test@example.com', PlatformUser.Role.SUPER_ADMIN)
        self.url = reverse('platform-messages-ses-test-send')

    @patch('communications.views.messages.send_ses_test_email')
    def test_provider_rejection_is_audited(self, mock_send):
        mock_send.return_value = {
            'ok': False,
            'error': 'AccessDenied on identity/christian@ayadata.ai',
        }

        response = self.client.post(
            self.url,
            {
                'to': 'christian@ayadata.ai',
                'subject': 'Fee reminder',
                'message': 'This body must stay out of the audit log.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400, response.data)
        entry = PlatformAuditLog.objects.get(action='messages.ses_test.failed')
        self.assertEqual(entry.target_type, 'ses_test')
        self.assertEqual(entry.detail['to'], 'christian@ayadata.ai')
        self.assertEqual(entry.detail['subject'], 'Fee reminder')
        self.assertIn('AccessDenied', entry.detail['error'])
        self.assertNotIn('body', entry.detail)
        self.assertNotIn('This body must stay out of the audit log.', str(entry.detail))

    def test_blank_subject_is_not_audited(self):
        response = self.client.post(
            self.url,
            {'to': 'christian@ayadata.ai', 'subject': '', 'message': 'Hello'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(PlatformAuditLog.objects.filter(target_type='ses_test').exists())
