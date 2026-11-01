from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings

from accounts.tests.factories import create_user, user_school
from notifications.models import GuardianDelivery
from notifications.services.guardians import (
    notify_guardians_ward_enrolled,
    resolve_channels,
)
from schools.models import SchoolSettings
from schools.services.settings import get_school_settings
from schools.tests.factories import create_active_term
from students.models import Parent, StudentParent
from students.tests.factories import create_student, ensure_default_stream
from academics.models import ClassLevel, Level


SEND_SMS_PATH = 'shared.services.arkesel_sms.send_sms_to_recipients'


class ResolveChannelsTests(TestCase):
    def setUp(self):
        self.admin = create_user(is_active=True)
        self.school = user_school(self.admin)

    def test_intersects_school_parent_and_contacts(self):
        parent = Parent.objects.create(
            school=self.school,
            name='Ama',
            phone_number='+233244000001',
            email='ama@example.com',
            notify_channel=Parent.NotifyChannel.BOTH,
        )
        self.assertEqual(
            resolve_channels(school_channels='both', parent=parent),
            {'sms', 'email'},
        )

        parent.notify_channel = Parent.NotifyChannel.SMS
        parent.save(update_fields=['notify_channel', 'updated_at'])
        self.assertEqual(
            resolve_channels(school_channels='both', parent=parent),
            {'sms'},
        )

        parent.email = ''
        parent.notify_channel = Parent.NotifyChannel.EMAIL
        parent.save(update_fields=['email', 'notify_channel', 'updated_at'])
        self.assertEqual(resolve_channels(school_channels='both', parent=parent), set())


class WardEnrolledNotifyTests(TestCase):
    def setUp(self):
        self.admin = create_user(is_active=True)
        self.school = user_school(self.admin)
        create_active_term(self.school)
        level = Level.objects.create(
            school=self.school,
            name='Primary',
            is_system_generated=False,
        )
        class_level = ClassLevel.objects.create(
            school=self.school,
            level=level,
            name='P1',
            is_system_generated=False,
        )
        self.stream = ensure_default_stream(class_level)
        self.student = create_student(school=self.school, student_id='G-0001')
        self.primary = Parent.objects.create(
            school=self.school,
            name='Primary Parent',
            phone_number='+233244000010',
            email='primary@example.com',
            notify_channel=Parent.NotifyChannel.BOTH,
        )
        self.secondary = Parent.objects.create(
            school=self.school,
            name='Secondary Parent',
            phone_number='+233244000011',
            email='secondary@example.com',
            notify_channel=Parent.NotifyChannel.BOTH,
        )
        StudentParent.objects.create(
            student=self.student,
            parent=self.primary,
            relationship=StudentParent.RelationshipChoices.FATHER,
            is_primary=True,
        )
        StudentParent.objects.create(
            student=self.student,
            parent=self.secondary,
            relationship=StudentParent.RelationshipChoices.MOTHER,
            is_primary=False,
        )
        get_school_settings(self.school)

    @patch(SEND_SMS_PATH, return_value={'status': 'success', 'data': [{'id': 'sms-1'}]})
    @override_settings(DEBUG=True)
    def test_notifies_primary_by_default(self, mock_sms):
        notify_guardians_ward_enrolled(
            student=self.student,
            class_name=self.stream.full_name,
        )

        self.assertEqual(mock_sms.call_count, 1)
        self.assertEqual(mock_sms.call_args.args[0], [self.primary.phone_number])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['primary@example.com'])
        self.assertEqual(
            GuardianDelivery.objects.filter(
                event_type=GuardianDelivery.EventType.WARD_ENROLLED,
                status=GuardianDelivery.Status.SENT,
            ).count(),
            2,
        )

    @patch(SEND_SMS_PATH, return_value={'status': 'success'})
    def test_respects_all_audience(self, mock_sms):
        settings_row = get_school_settings(self.school)
        settings_row.guardian_audience = SchoolSettings.GuardianAudience.ALL
        settings_row.save(update_fields=['guardian_audience', 'updated_at'])

        notify_guardians_ward_enrolled(student=self.student, class_name='P1')

        # Identical SMS bodies are batched into one Arkesel request.
        self.assertEqual(mock_sms.call_count, 1)
        self.assertEqual(len(mock_sms.call_args.args[0]), 2)
        self.assertEqual(len(mail.outbox), 2)

    @patch(SEND_SMS_PATH, return_value={'status': 'success'})
    def test_disabled_event_sends_nothing(self, mock_sms):
        settings_row = get_school_settings(self.school)
        settings_row.guardian_ward_enrolled_enabled = False
        settings_row.save(update_fields=['guardian_ward_enrolled_enabled', 'updated_at'])

        notify_guardians_ward_enrolled(student=self.student, class_name='P1')

        mock_sms.assert_not_called()
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(GuardianDelivery.objects.count(), 0)

    @patch(SEND_SMS_PATH, return_value={'status': 'success'})
    def test_idempotent_resend_does_not_duplicate(self, mock_sms):
        notify_guardians_ward_enrolled(student=self.student, class_name='P1')
        first_count = GuardianDelivery.objects.count()
        notify_guardians_ward_enrolled(student=self.student, class_name='P1')
        self.assertEqual(GuardianDelivery.objects.count(), first_count)
        self.assertEqual(mock_sms.call_count, 1)
        self.assertEqual(len(mail.outbox), 1)
