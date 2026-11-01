from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from academics.models import ClassLevel, Level
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from fees.models import FeeItem, FeeStructure, StudentFee
from fees.services import apply_fee_structure, publish_fee_structure
from fees.services.fee_schedule_links import (
    build_fee_schedule_public_url,
    make_fee_schedule_token,
)
from fees.services.fees import ensure_enrollment_fees
from notifications.models import GuardianDelivery
from schools.models import AcademicYear, SchoolSettings, Term
from schools.services.settings import get_school_settings
from students.models import Parent, StudentParent
from students.tests.factories import create_student, enroll_student, ensure_default_stream

SEND_SMS_PATH = 'shared.services.arkesel_sms.send_sms_to_recipients'


class NextTermFeeNoticeTests(APITestCase):
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
        self.class_level = ClassLevel.objects.create(
            school=self.school,
            level=level,
            name='JHS 1',
            is_system_generated=False,
        )
        self.stream = ensure_default_stream(self.class_level)

        self.student = create_student(
            school=self.school,
            student_id='NT-0001',
            first_name='Ama',
            last_name='Mensah',
        )
        self.enrollment = enroll_student(
            student=self.student,
            term=self.term,
            stream=self.stream,
            is_new_student=True,
        )
        parent = Parent.objects.create(
            school=self.school,
            name='Parent Ama',
            phone_number='+233244009901',
            email='nt-0001@example.com',
            notify_channel=Parent.NotifyChannel.BOTH,
        )
        StudentParent.objects.create(
            student=self.student,
            parent=parent,
            relationship=StudentParent.RelationshipChoices.FATHER,
            is_primary=True,
        )

        self.structure = FeeStructure.objects.create(
            school=self.school,
            term=self.term,
            created_by=self.user,
        )
        FeeItem.objects.create(
            fee_structure=self.structure,
            name='Tuition Fee',
            amount=Decimal('500.00'),
            applies_to_type=FeeItem.AppliesToType.SCHOOL,
            student_type=FeeItem.StudentType.ALL_STUDENTS,
        )
        FeeItem.objects.create(
            fee_structure=self.structure,
            name='New student levy',
            amount=Decimal('50.00'),
            applies_to_type=FeeItem.AppliesToType.SCHOOL,
            student_type=FeeItem.StudentType.NEW_STUDENT,
        )
        publish_fee_structure(self.structure)

        settings_row = get_school_settings(self.school)
        settings_row.guardian_next_term_fees_enabled = True
        settings_row.guardian_next_term_fees_channels = SchoolSettings.GuardianChannel.BOTH
        settings_row.save()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    @patch(SEND_SMS_PATH, return_value={'status': 'success', 'data': [{'id': 'nt-1'}]})
    def test_apply_queues_per_student_schedule_notice(self, mock_sms):
        mail.outbox.clear()
        with self.captureOnCommitCallbacks(execute=True):
            apply_fee_structure(self.structure)

        self.assertEqual(StudentFee.objects.filter(student=self.student).count(), 2)
        mock_sms.assert_called_once()
        message = mock_sms.call_args.args[1]
        self.assertIn('550.00', message)
        self.assertIn('/api/v1/public/fee-schedules/', message)
        self.assertEqual(
            GuardianDelivery.objects.filter(
                event_type=GuardianDelivery.EventType.NEXT_TERM_FEES,
                channel=GuardianDelivery.Channel.SMS,
                status=GuardianDelivery.Status.SENT,
            ).count(),
            1,
        )
        self.assertEqual(
            GuardianDelivery.objects.filter(
                event_type=GuardianDelivery.EventType.NEXT_TERM_FEES,
                channel=GuardianDelivery.Channel.EMAIL,
                status=GuardianDelivery.Status.SENT,
            ).count(),
            1,
        )
        self.assertGreaterEqual(len(mail.outbox), 1)
        bodies = '\n'.join(item.body for item in mail.outbox)
        self.assertIn('Tuition Fee', bodies)
        self.assertIn('New student levy', bodies)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    @patch(SEND_SMS_PATH, return_value={'status': 'success'})
    def test_disabled_setting_skips_notice(self, mock_sms):
        settings_row = get_school_settings(self.school)
        settings_row.guardian_next_term_fees_enabled = False
        settings_row.save(update_fields=['guardian_next_term_fees_enabled', 'updated_at'])

        with self.captureOnCommitCallbacks(execute=True):
            apply_fee_structure(self.structure)

        mock_sms.assert_not_called()
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(
            GuardianDelivery.objects.filter(
                event_type=GuardianDelivery.EventType.NEXT_TERM_FEES,
            ).count(),
            0,
        )

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    @patch(SEND_SMS_PATH, return_value={'status': 'success', 'data': [{'id': 'nt-2'}]})
    def test_late_enrollment_is_idempotent_with_apply(self, mock_sms):
        with self.captureOnCommitCallbacks(execute=True):
            apply_fee_structure(self.structure)

        first_sms = mock_sms.call_count
        first_mail = len(mail.outbox)
        first_deliveries = GuardianDelivery.objects.filter(
            event_type=GuardianDelivery.EventType.NEXT_TERM_FEES,
        ).count()

        with self.captureOnCommitCallbacks(execute=True):
            ensure_enrollment_fees(self.enrollment)

        self.assertEqual(mock_sms.call_count, first_sms)
        self.assertEqual(len(mail.outbox), first_mail)
        self.assertEqual(
            GuardianDelivery.objects.filter(
                event_type=GuardianDelivery.EventType.NEXT_TERM_FEES,
            ).count(),
            first_deliveries,
        )

    def test_public_fee_schedule_page_lists_items(self):
        apply_fee_structure(self.structure)
        token = make_fee_schedule_token(student_id=self.student.id, term_id=self.term.id)
        url = reverse('public-fee-schedule', kwargs={'token': token})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tuition Fee')
        self.assertContains(response, 'New student levy')
        self.assertContains(response, 'GHS 550.00')
        self.assertContains(response, 'Ama')
        self.assertIn(
            '/api/v1/public/fee-schedules/',
            build_fee_schedule_public_url(
                student_id=self.student.id,
                term_id=self.term.id,
            ),
        )

    def test_public_fee_schedule_rejects_bad_token(self):
        response = self.client.get(
            reverse('public-fee-schedule', kwargs={'token': 'not-valid'}),
        )
        self.assertEqual(response.status_code, 400)
