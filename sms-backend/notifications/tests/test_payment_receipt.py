from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from academics.models import ClassLevel, Level
from accounts.tests.factories import create_user, user_school
from communications.tests.helpers import seed_test_credits
from fees.models import FeeItem, FeeStructure, Payment, Receipt
from fees.services import apply_fee_structure, publish_fee_structure
from fees.services.payments import record_student_payment
from fees.services.receipts import build_receipt_public_url, make_receipt_token
from notifications.models import GuardianDelivery
from notifications.services.guardians import notify_guardians_payment_receipt
from schools.models import AcademicYear, SchoolSettings, Term
from schools.services.settings import get_school_settings
from students.models import Parent, StudentParent
from students.tests.factories import create_student, enroll_student, ensure_default_stream

SEND_SMS_PATH = 'shared.services.arkesel_sms.send_sms_to_recipients'


class PaymentReceiptNotifyTests(TestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
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
        self.student = create_student(
            school=self.school,
            student_id='PR-0001',
            first_name='Kofi',
            last_name='Asante',
        )
        enroll_student(
            student=self.student,
            term=self.term,
            stream=stream,
            is_new_student=True,
        )
        self.parent = Parent.objects.create(
            school=self.school,
            name='Guardian',
            phone_number='+233244000099',
            email='guardian@example.com',
            notify_channel=Parent.NotifyChannel.BOTH,
        )
        StudentParent.objects.create(
            student=self.student,
            parent=self.parent,
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
        settings_row.guardian_payment_receipt_enabled = True
        settings_row.guardian_payment_receipt_channels = SchoolSettings.GuardianChannel.BOTH
        settings_row.save()
        seed_test_credits(self.school)

    def _record_payment(self):
        with self.captureOnCommitCallbacks(execute=True):
            return record_student_payment(
                school=self.school,
                student=self.student,
                amount=Decimal('150.00'),
                payment_method=Payment.PaymentMethod.CASH,
                paid_at=timezone.now(),
                recorded_by=self.user,
            )

    @patch(SEND_SMS_PATH, return_value={'status': 'success', 'data': [{'id': 'pay-sms-1'}]})
    def test_record_payment_notifies_when_enabled(self, mock_sms):
        result = self._record_payment()

        self.assertEqual(mock_sms.call_count, 1)
        self.assertIn(result['receipt_number'], mock_sms.call_args.args[1])
        self.assertIn('/api/v1/public/receipts/', mock_sms.call_args.args[1])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(result['receipt_number'], mail.outbox[0].subject)
        self.assertEqual(
            GuardianDelivery.objects.filter(
                event_type=GuardianDelivery.EventType.PAYMENT_RECEIPT,
                status__in=(
                    GuardianDelivery.Status.SUBMITTED,
                    GuardianDelivery.Status.SENT,
                ),
            ).count(),
            2,
        )

    @patch(SEND_SMS_PATH, return_value={'status': 'success'})
    def test_disabled_setting_skips_notify(self, mock_sms):
        settings_row = get_school_settings(self.school)
        settings_row.guardian_payment_receipt_enabled = False
        settings_row.save(update_fields=['guardian_payment_receipt_enabled', 'updated_at'])

        self._record_payment()

        mock_sms.assert_not_called()
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(
            GuardianDelivery.objects.filter(
                event_type=GuardianDelivery.EventType.PAYMENT_RECEIPT,
            ).count(),
            0,
        )

    @patch(SEND_SMS_PATH, return_value={'status': 'success'})
    def test_public_receipt_page_renders(self, mock_sms):
        result = self._record_payment()
        receipt = Receipt.objects.get(id=result['receipt_id'])
        url = reverse('public-receipt', kwargs={'token': make_receipt_token(receipt.id)})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, receipt.receipt_number)
        self.assertContains(response, 'Kofi')
        self.assertContains(response, 'GHS')

    def test_public_receipt_rejects_bad_token(self):
        response = self.client.get(reverse('public-receipt', kwargs={'token': 'not-valid'}))
        self.assertEqual(response.status_code, 400)

    @patch(SEND_SMS_PATH, return_value={'status': 'success'})
    def test_notify_includes_built_url(self, mock_sms):
        payment = Payment.objects.create(
            student=self.student,
            term=self.term,
            amount=Decimal('50.00'),
            payment_method=Payment.PaymentMethod.CASH,
            recorded_by=self.user,
        )
        receipt = Receipt.objects.create(
            payment=payment,
            receipt_number='RCPT-TEST-0001',
            issued_by=self.user,
        )
        expected = build_receipt_public_url(receipt.id)

        notify_guardians_payment_receipt(
            student=self.student,
            payment_id=payment.id,
            receipt_id=receipt.id,
            receipt_number=receipt.receipt_number,
            amount=payment.amount,
        )

        self.assertIn(expected, mock_sms.call_args.args[1])
        self.assertIn(expected, mail.outbox[0].body)
