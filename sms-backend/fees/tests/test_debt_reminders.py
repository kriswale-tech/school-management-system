from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, Level
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from fees.models import FeeItem, FeeStructure
from fees.services import apply_fee_structure, publish_fee_structure
from notifications.models import GuardianDelivery
from schools.models import AcademicYear, SchoolSettings, Term
from schools.services.settings import get_school_settings
from students.models import Parent, StudentParent
from students.tests.factories import create_student, enroll_student, ensure_default_stream

SEND_SMS_PATH = 'shared.services.arkesel_sms.send_sms_to_recipients'


class DebtReminderAPITests(APITestCase):
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
        self.stream = ensure_default_stream(class_level)
        self.debtor = create_student(
            school=self.school,
            student_id='DR-0001',
            first_name='Ama',
            last_name='Mensah',
        )
        self.paid = create_student(
            school=self.school,
            student_id='DR-0002',
            first_name='Kojo',
            last_name='Boateng',
        )
        for student in (self.debtor, self.paid):
            enroll_student(
                student=student,
                term=self.term,
                stream=self.stream,
                is_new_student=True,
            )
            parent = Parent.objects.create(
                school=self.school,
                name=f'Parent {student.first_name}',
                phone_number=f'+23324400{student.student_id[-4:]}01',
                email=f'{student.student_id.lower()}@example.com',
                notify_channel=Parent.NotifyChannel.BOTH,
            )
            StudentParent.objects.create(
                student=student,
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

        # Fully pay Kojo so only Ama is a debtor.
        from fees.services.payments import record_student_payment
        from fees.models import Payment
        from django.utils import timezone

        record_student_payment(
            school=self.school,
            student=self.paid,
            amount=Decimal('500.00'),
            payment_method=Payment.PaymentMethod.CASH,
            paid_at=timezone.now(),
            recorded_by=self.user,
        )

        settings_row = get_school_settings(self.school)
        settings_row.guardian_debt_reminder_enabled = True
        settings_row.guardian_debt_reminder_channels = SchoolSettings.GuardianChannel.BOTH
        settings_row.save()

        self.preview_url = reverse('debt-reminder-preview')
        self.send_url = reverse('debt-reminder-send')

    def test_preview_counts_only_debtors(self):
        response = self.client.post(
            self.preview_url,
            {
                'term_id': str(self.term.id),
                'student_ids': [str(self.debtor.id), str(self.paid.id)],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['enabled'])
        self.assertEqual(response.data['eligible_count'], 1)
        self.assertEqual(response.data['skipped_count'], 1)
        self.assertEqual(response.data['sms_count'], 1)
        self.assertEqual(response.data['email_count'], 1)
        self.assertEqual(response.data['eligible_ids'], [str(self.debtor.id)])

    def test_preview_when_disabled(self):
        settings_row = get_school_settings(self.school)
        settings_row.guardian_debt_reminder_enabled = False
        settings_row.save(update_fields=['guardian_debt_reminder_enabled', 'updated_at'])

        response = self.client.post(
            self.preview_url,
            {
                'term_id': str(self.term.id),
                'student_ids': [str(self.debtor.id)],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['enabled'])
        self.assertEqual(response.data['sms_count'], 0)

    @patch(SEND_SMS_PATH, return_value={'status': 'success', 'data': [{'id': 'debt-1'}]})
    def test_send_creates_deliveries(self, mock_sms):
        response = self.client.post(
            self.send_url,
            {
                'term_id': str(self.term.id),
                'student_ids': [str(self.debtor.id), str(self.paid.id)],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['queued'])
        self.assertEqual(response.data['students_notified'], 1)
        self.assertEqual(response.data['sms_sent'], 1)
        self.assertEqual(response.data['email_sent'], 1)
        mock_sms.assert_called_once()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            GuardianDelivery.objects.filter(
                event_type=GuardianDelivery.EventType.DEBT_REMINDER,
                status=GuardianDelivery.Status.SENT,
            ).count(),
            2,
        )

    def test_selection_ids_returns_all_debtors_for_filters(self):
        url = reverse('fee-desk-selection-ids')
        response = self.client.get(url, {'term': str(self.term.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['student_ids'], [str(self.debtor.id)])

        debtors_only = self.client.get(
            url,
            {'term': str(self.term.id), 'debtors': 'true'},
        )
        self.assertEqual(debtors_only.status_code, status.HTTP_200_OK)
        self.assertEqual(debtors_only.data['count'], 1)

    def test_send_rejects_when_disabled(self):
        settings_row = get_school_settings(self.school)
        settings_row.guardian_debt_reminder_enabled = False
        settings_row.save(update_fields=['guardian_debt_reminder_enabled', 'updated_at'])

        response = self.client.post(
            self.send_url,
            {
                'term_id': str(self.term.id),
                'student_ids': [str(self.debtor.id)],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_rejects_empty_eligible(self):
        response = self.client.post(
            self.send_url,
            {
                'term_id': str(self.term.id),
                'student_ids': [str(self.paid.id)],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
