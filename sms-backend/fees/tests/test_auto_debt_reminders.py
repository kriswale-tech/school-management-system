from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from academics.models import ClassLevel, Level
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from fees.models import FeeItem, FeeStructure
from fees.services import apply_fee_structure, publish_fee_structure
from fees.services.auto_debt_reminders import (
    auto_debt_reminder_period_key,
    is_auto_debt_reminder_due,
    process_school_auto_debt_reminders,
    run_auto_debt_reminders,
)
from notifications.models import GuardianDelivery
from schools.models import AcademicYear, SchoolSettings, Term
from schools.services.settings import get_school_settings
from students.models import Parent, StudentParent
from students.tests.factories import create_student, enroll_student, ensure_default_stream

SEND_SMS_PATH = 'shared.services.arkesel_sms.send_sms_to_recipients'


class AutoDebtReminderScheduleTests(SimpleTestCase):
    def test_end_of_month_due_only_on_last_day(self):
        freq = SchoolSettings.DebtReminderFrequency.END_OF_MONTH
        self.assertTrue(is_auto_debt_reminder_due(frequency=freq, today=date(2026, 2, 28)))
        self.assertFalse(is_auto_debt_reminder_due(frequency=freq, today=date(2026, 2, 27)))
        self.assertEqual(
            auto_debt_reminder_period_key(freq, date(2026, 2, 28)),
            '2026-02',
        )

    def test_weekly_due_on_monday(self):
        freq = SchoolSettings.DebtReminderFrequency.WEEKLY
        self.assertTrue(is_auto_debt_reminder_due(frequency=freq, today=date(2026, 3, 2)))  # Mon
        self.assertFalse(is_auto_debt_reminder_due(frequency=freq, today=date(2026, 3, 3)))

    def test_biweekly_due_on_even_iso_week_monday(self):
        freq = SchoolSettings.DebtReminderFrequency.BIWEEKLY
        # 2026-03-02 is ISO week 10 (even) Monday
        self.assertTrue(is_auto_debt_reminder_due(frequency=freq, today=date(2026, 3, 2)))
        # 2026-03-09 is ISO week 11 (odd) Monday
        self.assertFalse(is_auto_debt_reminder_due(frequency=freq, today=date(2026, 3, 9)))


class AutoDebtReminderProcessTests(APITestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        set_client_auth_cookies(self.client, self.user)
        self.school = user_school(self.user)
        self.academic_year = AcademicYear.objects.create(
            school=self.school,
            academic_year='2025/2026',
            start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31),
            is_active=True,
        )
        self.term = Term.objects.create(
            school=self.school,
            academic_year=self.academic_year,
            term=Term.TermChoices.FIRST_TERM,
            start_date=date(2025, 9, 1),
            end_date=date(2025, 12, 15),
            is_active=True,
        )
        level = Level.objects.create(
            school=self.school,
            name='Junior High',
            is_system_generated=False,
        )
        class_level = ClassLevel.objects.create(
            school=self.school,
            level=level,
            name='JHS 1',
            is_system_generated=False,
        )
        stream = ensure_default_stream(class_level)
        self.debtor = create_student(
            school=self.school,
            student_id='AD-0001',
            first_name='Ama',
            last_name='Mensah',
        )
        enroll_student(
            student=self.debtor,
            term=self.term,
            stream=stream,
            is_new_student=True,
        )
        parent = Parent.objects.create(
            school=self.school,
            name='Parent Ama',
            phone_number='+233244008801',
            email='ad-0001@example.com',
            notify_channel=Parent.NotifyChannel.BOTH,
        )
        StudentParent.objects.create(
            student=self.debtor,
            parent=parent,
            relationship=StudentParent.RelationshipChoices.FATHER,
            is_primary=True,
        )

        structure = FeeStructure.objects.create(
            school=self.school,
            term=self.term,
            created_by=self.user,
        )
        FeeItem.objects.create(
            fee_structure=structure,
            name='Tuition Fee',
            amount=Decimal('500.00'),
            applies_to_type=FeeItem.AppliesToType.SCHOOL,
            student_type=FeeItem.StudentType.ALL_STUDENTS,
        )
        publish_fee_structure(structure)
        apply_fee_structure(structure)

        settings_row = get_school_settings(self.school)
        settings_row.guardian_debt_reminder_enabled = True
        settings_row.guardian_debt_reminder_channels = SchoolSettings.GuardianChannel.BOTH
        settings_row.guardian_debt_reminder_auto_enabled = True
        settings_row.guardian_debt_reminder_frequency = (
            SchoolSettings.DebtReminderFrequency.END_OF_MONTH
        )
        settings_row.save()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    @patch(SEND_SMS_PATH, return_value={'status': 'success', 'data': [{'id': 'auto-1'}]})
    def test_process_queues_on_end_of_month(self, mock_sms):
        result = process_school_auto_debt_reminders(
            school_id=self.school.id,
            today=date(2026, 1, 31),
        )
        self.assertEqual(result['queued_students'], 1)
        self.assertEqual(result['sms'], 1)
        self.assertEqual(result['email'], 1)
        mock_sms.assert_called_once()
        self.assertGreaterEqual(len(mail.outbox), 1)
        self.assertEqual(
            GuardianDelivery.objects.filter(
                event_type=GuardianDelivery.EventType.DEBT_REMINDER,
                status=GuardianDelivery.Status.SENT,
            ).count(),
            2,
        )

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    @patch(SEND_SMS_PATH, return_value={'status': 'success'})
    def test_process_skips_when_not_due(self, mock_sms):
        result = process_school_auto_debt_reminders(
            school_id=self.school.id,
            today=date(2026, 1, 15),
        )
        self.assertEqual(result['skipped'], 'not_due')
        mock_sms.assert_not_called()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    @patch(SEND_SMS_PATH, return_value={'status': 'success', 'data': [{'id': 'auto-2'}]})
    def test_idempotent_within_same_period(self, mock_sms):
        process_school_auto_debt_reminders(school_id=self.school.id, today=date(2026, 1, 31))
        first_count = GuardianDelivery.objects.filter(
            event_type=GuardianDelivery.EventType.DEBT_REMINDER,
        ).count()
        process_school_auto_debt_reminders(school_id=self.school.id, today=date(2026, 1, 31))
        self.assertEqual(
            GuardianDelivery.objects.filter(
                event_type=GuardianDelivery.EventType.DEBT_REMINDER,
            ).count(),
            first_count,
        )
        self.assertEqual(mock_sms.call_count, 1)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    @patch('fees.tasks.process_school_auto_debt_reminders_task.delay')
    def test_run_fans_out_only_due_schools(self, mock_delay):
        result = run_auto_debt_reminders(today=date(2026, 1, 31))
        self.assertEqual(result['schools_due'], 1)
        mock_delay.assert_called_once()

        mock_delay.reset_mock()
        result = run_auto_debt_reminders(today=date(2026, 1, 15))
        self.assertEqual(result['schools_due'], 0)
        mock_delay.assert_not_called()

    def test_settings_api_exposes_auto_fields(self):
        response = self.client.patch(
            reverse('school-settings'),
            {
                'guardian_debt_reminder_enabled': True,
                'guardian_debt_reminder_auto_enabled': True,
                'guardian_debt_reminder_frequency': 'weekly',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['guardian_debt_reminder_auto_enabled'])
        self.assertEqual(response.data['guardian_debt_reminder_frequency'], 'weekly')
