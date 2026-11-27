from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.tests.factories import create_school
from platform_admin.models import PlatformAuditLog, PlatformUser
from platform_admin.services.audit import record_audit


class PlatformAuditListTests(APITestCase):
    def setUp(self):
        self.user = PlatformUser.objects.create_user(
            email='audit-admin@example.com',
            password='SecurePass123!',
            role=PlatformUser.Role.SUPER_ADMIN,
            first_name='Ada',
            last_name='Admin',
        )
        self.school = create_school(name='Ridge School', phone_number='+233244911001')
        self.sms = record_audit(
            actor=self.user,
            action='messages.arkesel_test.sent',
            target_type='arkesel_test',
            target_id='sms-1',
            detail={'to': '+233244000000', 'sandbox': True},
        )
        self.status_change = record_audit(
            actor=self.user,
            action='platform.school.status_changed',
            target_type='school',
            target_id=str(self.school.pk),
            detail={'from': 'pending', 'to': 'active', 'reason': 'Ready'},
        )
        PlatformAuditLog.objects.filter(pk=self.sms.pk).update(
            created_at=timezone.now() - timezone.timedelta(minutes=1),
        )
        self.client = self._client_for(self.user)
        self.url = reverse('platform-audit-list')

    def _client_for(self, user: PlatformUser):
        client = self.client_class()
        login = client.post(
            reverse('platform-login'),
            {'email': user.email, 'password': 'SecurePass123!'},
            format='json',
        )
        access = settings.PLATFORM_JWT['AUTH_COOKIE']
        client.cookies[access] = login.cookies[access].value
        return client

    def test_requires_a_signed_in_platform_user(self):
        response = self.client_class().get(self.url)
        self.assertIn(
            response.status_code,
            {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN},
        )

    def test_lists_newest_first_with_school_name(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertGreaterEqual(response.data['count'], 2)
        actions = [row['action'] for row in response.data['results']]
        self.assertLess(actions.index('platform.school.status_changed'), actions.index('messages.arkesel_test.sent'))
        school_row = next(row for row in response.data['results'] if row['id'] == str(self.status_change.pk))
        self.assertEqual(school_row['target_label'], 'Ridge School')
        self.assertEqual(school_row['actor_email'], 'audit-admin@example.com')
        self.assertEqual(school_row['actor_name'], 'Ada Admin')

    def test_filters_by_search_action_and_target(self):
        by_target_id = self.client.get(self.url, {'q': 'sms-1'})
        self.assertEqual(by_target_id.status_code, status.HTTP_200_OK)
        self.assertTrue(any(row['target_id'] == 'sms-1' for row in by_target_id.data['results']))

        by_email = self.client.get(self.url, {'q': 'audit-admin'})
        self.assertGreaterEqual(by_email.data['count'], 2)

        by_action = self.client.get(self.url, {'action': 'messages'})
        self.assertTrue(all(row['action'].startswith('messages') for row in by_action.data['results']))

        by_target = self.client.get(self.url, {'target_type': 'school'})
        self.assertTrue(all(row['target_type'] == 'school' for row in by_target.data['results']))
        self.assertTrue(any(row['id'] == str(self.status_change.pk) for row in by_target.data['results']))

    def test_filters_by_date(self):
        PlatformAuditLog.objects.filter(pk=self.sms.pk).update(
            created_at=timezone.now() - timezone.timedelta(days=10),
        )
        today = timezone.localdate().isoformat()
        response = self.client.get(self.url, {'start': today, 'end': today})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {row['id'] for row in response.data['results']}
        self.assertNotIn(str(self.sms.pk), ids)
        self.assertIn(str(self.status_change.pk), ids)
