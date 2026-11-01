from django.core import mail
from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import User
from accounts.tests.factories import create_user, user_school
from notifications.models import Notification
from notifications.services.emit import notify
from notifications.services.send_email import deliver_notification_email
from schools.tests.factories import create_active_term


class NotificationEmailDeliveryTests(APITestCase):
    def setUp(self):
        self.admin = create_user(is_active=True, email='admin@test.com')
        self.school = user_school(self.admin)
        self.school.name = 'Riverside Academy'
        self.school.setup_completed = True
        self.school.save(update_fields=['name', 'setup_completed', 'updated_at'])
        create_active_term(self.school)
        self.admin_membership = self.admin.memberships.select_related('user').get(
            school=self.school,
        )

        self.staff = create_user(
            phone_number='+233200000041',
            email='staff@test.com',
            school=self.school,
            role=User.RoleChoices.STAFF,
            is_active=True,
        )
        self.staff_membership = self.staff.memberships.select_related('user').get(
            school=self.school,
        )

        self.no_email_user = create_user(
            phone_number='+233200000042',
            email='',
            school=self.school,
            role=User.RoleChoices.TEACHER,
            is_active=True,
        )
        self.no_email_membership = self.no_email_user.memberships.select_related(
            'user',
        ).get(school=self.school)

    @override_settings(EMAIL_ENABLED=True)
    def test_notify_queues_and_sends_when_recipient_has_email(self):
        with self.captureOnCommitCallbacks(execute=True):
            row = notify(
                school=self.school,
                recipient=self.staff_membership,
                event_type=Notification.EventType.MEMBER_INVITED,
                title='Added to school',
                body='You were added as Staff.',
                href='/staff',
                actor=self.admin,
            )
        self.assertIsNotNone(row)
        row.refresh_from_db()
        self.assertEqual(row.email_status, Notification.EmailStatus.SENT)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['staff@test.com'])
        self.assertIn('Riverside Academy', mail.outbox[0].subject)
        self.assertTrue(mail.outbox[0].alternatives)

    @override_settings(EMAIL_ENABLED=True)
    def test_notify_skips_email_without_address(self):
        row = notify(
            school=self.school,
            recipient=self.no_email_membership,
            event_type=Notification.EventType.CLASS_TEACHER_ASSIGNED,
            title='Class teacher assignment',
            body='You were assigned as class teacher.',
            href='/classes/1',
            actor=self.admin,
        )
        self.assertIsNotNone(row)
        row.refresh_from_db()
        self.assertEqual(row.email_status, Notification.EmailStatus.SKIPPED)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(EMAIL_ENABLED=False)
    def test_notify_does_not_queue_when_email_disabled(self):
        row = notify(
            school=self.school,
            recipient=self.staff_membership,
            event_type=Notification.EventType.TERM_OPENED,
            title='New term opened',
            body='First Term is now active.',
            href='/dashboard',
            actor=self.admin,
        )
        self.assertIsNotNone(row)
        row.refresh_from_db()
        self.assertEqual(row.email_status, Notification.EmailStatus.SKIPPED)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(EMAIL_ENABLED=True)
    def test_deliver_marks_failed_on_send_error(self):
        from unittest.mock import patch

        with self.captureOnCommitCallbacks(execute=False):
            row = notify(
                school=self.school,
                recipient=self.staff_membership,
                event_type=Notification.EventType.STUDENT_ENROLLED,
                title='New enrollment',
                body='Ama enrolled.',
                href='/students',
                actor=self.admin,
            )
        row.refresh_from_db()
        self.assertEqual(row.email_status, Notification.EmailStatus.PENDING)
        with patch(
            'notifications.services.send_email.EmailMultiAlternatives.send',
            side_effect=RuntimeError('resend unavailable'),
        ):
            status = deliver_notification_email(row.id)
        self.assertEqual(status, Notification.EmailStatus.FAILED)
        row.refresh_from_db()
        self.assertEqual(row.email_status, Notification.EmailStatus.FAILED)
