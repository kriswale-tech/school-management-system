from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.tests.factories import create_school, create_user, set_client_auth_cookies
from notifications.models import GuardianDelivery, GuardianMessageTemplate
from notifications.services.message_templates import compose_sms, upsert_template


class MessageTemplateApiTests(APITestCase):
    def setUp(self):
        self.school = create_school(name='Template School', phone_number='+233244710001')
        self.admin = create_user(
            school=self.school,
            is_active=True,
            phone_number='+233244710002',
            email='template-admin@test.com',
        )
        set_client_auth_cookies(self.client, self.admin)

    def test_list_templates_returns_defaults(self):
        response = self.client.get(reverse('messaging-templates'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        types = {row['event_type'] for row in response.data}
        self.assertEqual(
            types,
            {
                GuardianDelivery.EventType.WARD_ENROLLED,
                GuardianDelivery.EventType.PAYMENT_RECEIPT,
                GuardianDelivery.EventType.DEBT_REMINDER,
                GuardianDelivery.EventType.REPORT_READY,
                GuardianDelivery.EventType.NEXT_TERM_FEES,
            },
        )
        ward = next(row for row in response.data if row['event_type'] == 'ward_enrolled')
        self.assertFalse(ward['sms_body_is_custom'])
        self.assertIn('{{student_name}}', ward['sms_body'])

    def test_update_and_preview_sms(self):
        response = self.client.put(
            reverse('messaging-templates-update'),
            {
                'event_type': 'ward_enrolled',
                'sms_body': '{{student_name}} joined {{school_name}}{{class_part}}.',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = GuardianMessageTemplate.objects.get(
            school=self.school,
            event_type='ward_enrolled',
        )
        self.assertIn('joined', row.sms_body)

        preview = self.client.post(
            reverse('messaging-templates-preview'),
            {
                'event_type': 'ward_enrolled',
                'channel': 'sms',
                'sms_body': row.sms_body,
            },
            format='json',
        )
        self.assertEqual(preview.status_code, status.HTTP_200_OK)
        self.assertIn('Ama Mensah joined', preview.data['rendered'])
        self.assertIn('sms', preview.data)
        self.assertGreaterEqual(preview.data['sms']['segments'], 1)

    def test_restore_default_clears_custom(self):
        upsert_template(
            school=self.school,
            event_type='ward_enrolled',
            sms_body='Custom {{student_name}}',
        )
        response = self.client.put(
            reverse('messaging-templates-update'),
            {'event_type': 'ward_enrolled', 'restore': ['sms_body']},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ward = next(row for row in response.data if row['event_type'] == 'ward_enrolled')
        self.assertFalse(ward['sms_body_is_custom'])

    def test_compose_sms_uses_custom_body(self):
        upsert_template(
            school=self.school,
            event_type='ward_enrolled',
            sms_body='Hello {{student_name}}.',
        )
        body = compose_sms(
            school=self.school,
            event_type='ward_enrolled',
            context={
                'school_name': self.school.name,
                'student_name': 'Kojo',
                'class_part': '',
            },
        )
        self.assertIn('Hello Kojo.', body)
        self.assertIn('[Template School]:', body)
