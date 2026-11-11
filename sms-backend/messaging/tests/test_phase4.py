from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.tests.factories import create_school, create_user, set_client_auth_cookies
from notifications.models import GuardianDelivery
from students.models import Parent
from students.tests.factories import create_student


class MessagingPhase4Tests(APITestCase):
    def setUp(self):
        self.school = create_school(name='Messaging School', phone_number='+233244700001')
        self.admin = create_user(
            school=self.school,
            is_active=True,
            phone_number='+233244700002',
            email='messaging-admin@test.com',
        )
        set_client_auth_cookies(self.client, self.admin)
        self.parent = Parent.objects.create(
            school=self.school,
            name='Guardian One',
            phone_number='+233244700099',
        )
        self.student = create_student(school=self.school)
        self.failed = GuardianDelivery.objects.create(
            school=self.school,
            parent=self.parent,
            student=self.student,
            event_type=GuardianDelivery.EventType.DEBT_REMINDER,
            channel=GuardianDelivery.Channel.SMS,
            status=GuardianDelivery.Status.FAILED,
            recipient_address=self.parent.phone_number,
            body_preview='Please settle fees.',
            body_text='Please settle fees.',
            error_message='The SMS could not be sent.',
            user_error_message='The SMS could not be sent.',
            idempotency_key='orig-fail-1',
        )

    def test_overview_and_list(self):
        overview = self.client.get(reverse('messaging-overview'))
        self.assertEqual(overview.status_code, status.HTTP_200_OK)
        self.assertIn('credits', overview.data)
        self.assertEqual(overview.data['open_failures'], 1)
        self.assertEqual(overview.data['period'], '7d')
        breakdown = self.client.get(reverse('messaging-overview'), {'period': '30d'})
        self.assertEqual(breakdown.status_code, status.HTTP_200_OK)
        self.assertEqual(breakdown.data['period'], '30d')
        debt = [
            row
            for row in breakdown.data['usage']['by_event']
            if row['event_type'] == 'debt_reminder' and row['channel'] == 'sms'
        ]
        self.assertEqual(debt[0]['failed'], 1)

        listing = self.client.get(
            reverse('messaging-deliveries'),
            {'status': 'failed'},
        )
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data['count'], 1)
        self.assertEqual(listing.data['results'][0]['id'], str(self.failed.pk))

    def test_retry_failed_sms(self):
        with patch('messaging.services.enqueue_guardian_sms', return_value=1) as mocked:
            response = self.client.post(
                reverse('messaging-delivery-retry', kwargs={'pk': self.failed.pk}),
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['queued'], 1)
        mocked.assert_called_once()
        item = mocked.call_args.args[0][0]
        self.assertEqual(item['body'], 'Please settle fees.')
        self.assertEqual(item['source_delivery_id'], str(self.failed.pk))
        self.assertTrue(item['idempotency_key'].startswith(f'retry:{self.failed.pk}:'))

    def test_cannot_resend_submitted_sms(self):
        submitted = GuardianDelivery.objects.create(
            school=self.school,
            parent=self.parent,
            student=self.student,
            event_type=GuardianDelivery.EventType.DEBT_REMINDER,
            channel=GuardianDelivery.Channel.SMS,
            status=GuardianDelivery.Status.SUBMITTED,
            recipient_address=self.parent.phone_number,
            body_preview='Hi',
            body_text='Hi',
            provider_message_id='sms-1',
            idempotency_key='orig-sub-1',
        )
        response = self.client.post(
            reverse('messaging-delivery-retry', kwargs={'pk': submitted.pk}),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_overview_custom_date_range(self):
        response = self.client.get(
            reverse('messaging-overview'),
            {'start': '2020-01-01', 'end': '2020-01-31'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['period'], 'custom')
        self.assertEqual(response.data['period_start'], '2020-01-01')
        self.assertEqual(response.data['usage']['sms_failed'], 0)

    def test_bulk_retry_resends_only_eligible_messages(self):
        skipped = GuardianDelivery.objects.create(
            school=self.school,
            parent=self.parent,
            student=self.student,
            event_type=GuardianDelivery.EventType.DEBT_REMINDER,
            channel=GuardianDelivery.Channel.EMAIL,
            status=GuardianDelivery.Status.SKIPPED,
            recipient_address='parent@example.com',
            body_preview='Please settle fees.',
            body_text='Please settle fees.',
            idempotency_key='orig-skip-email',
        )
        submitted = GuardianDelivery.objects.create(
            school=self.school,
            parent=self.parent,
            student=self.student,
            event_type=GuardianDelivery.EventType.DEBT_REMINDER,
            channel=GuardianDelivery.Channel.SMS,
            status=GuardianDelivery.Status.SUBMITTED,
            recipient_address=self.parent.phone_number,
            body_preview='Hi',
            body_text='Hi',
            idempotency_key='orig-sub-bulk',
        )
        with (
            patch('messaging.services.enqueue_guardian_sms', return_value=1) as sms,
            patch('messaging.services.enqueue_guardian_email', return_value=1) as email,
        ):
            response = self.client.post(
                reverse('messaging-delivery-bulk-retry'),
                {'ids': [str(self.failed.pk), str(skipped.pk), str(submitted.pk)]},
                format='json',
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['queued'], 2)
        self.assertEqual(len(response.data['skipped']), 1)
        self.assertEqual(response.data['skipped'][0]['id'], str(submitted.pk))
        sms.assert_called_once()
        email.assert_called_once()

    def test_eligible_selection_follows_filters_and_skips_ineligible(self):
        skipped = GuardianDelivery.objects.create(
            school=self.school,
            parent=self.parent,
            student=self.student,
            event_type=GuardianDelivery.EventType.REPORT_READY,
            channel=GuardianDelivery.Channel.EMAIL,
            status=GuardianDelivery.Status.SKIPPED,
            recipient_address='parent@example.com',
            body_preview='Report ready',
            body_text='',
            segments=0,
            idempotency_key='eligible-skip-email',
        )
        GuardianDelivery.objects.create(
            school=self.school,
            parent=self.parent,
            student=self.student,
            event_type=GuardianDelivery.EventType.DEBT_REMINDER,
            channel=GuardianDelivery.Channel.SMS,
            status=GuardianDelivery.Status.SUBMITTED,
            recipient_address=self.parent.phone_number,
            body_preview='Already sent',
            body_text='Already sent',
            idempotency_key='eligible-submitted',
        )
        GuardianDelivery.objects.create(
            school=self.school,
            parent=self.parent,
            student=self.student,
            event_type=GuardianDelivery.EventType.DEBT_REMINDER,
            channel=GuardianDelivery.Channel.SMS,
            status=GuardianDelivery.Status.FAILED,
            recipient_address=self.parent.phone_number,
            body_preview='',
            body_text='',
            idempotency_key='eligible-empty-body',
        )
        self.failed.segments = 2
        self.failed.save(update_fields=['segments'])

        response = self.client.get(reverse('messaging-delivery-eligible'))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['total'], 2)
        self.assertFalse(response.data['capped'])
        ids = {str(item) for item in response.data['ids']}
        self.assertEqual(ids, {str(self.failed.pk), str(skipped.pk)})
        self.assertEqual(response.data['sms_credits'], 2)
        self.assertEqual(response.data['email_credits'], 1)

        sms_only = self.client.get(
            reverse('messaging-delivery-eligible'),
            {'channel': 'sms', 'status': 'failed'},
        )
        self.assertEqual(sms_only.status_code, status.HTTP_200_OK)
        self.assertEqual(sms_only.data['total'], 1)
        self.assertEqual(str(sms_only.data['ids'][0]), str(self.failed.pk))

    def test_arkesel_dlr_webhook_updates_status(self):
        row = GuardianDelivery.objects.create(
            school=self.school,
            parent=self.parent,
            student=self.student,
            event_type=GuardianDelivery.EventType.REPORT_READY,
            channel=GuardianDelivery.Channel.SMS,
            status=GuardianDelivery.Status.SUBMITTED,
            recipient_address=self.parent.phone_number,
            body_preview='Report ready',
            body_text='Report ready',
            provider_message_id='ark-dlr-1',
            idempotency_key='dlr-1',
        )
        url = reverse('arkesel-sms-dlr-webhook')
        first = self.client.get(url, {'sms_id': 'ark-dlr-1', 'status': 'DELIVERED'})
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        row.refresh_from_db()
        self.assertEqual(row.status, GuardianDelivery.Status.DELIVERED)
        # Idempotent duplicate callback
        second = self.client.get(url, {'sms_id': 'ark-dlr-1', 'status': 'DELIVERED'})
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        row.refresh_from_db()
        self.assertEqual(row.status, GuardianDelivery.Status.DELIVERED)
