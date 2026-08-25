from datetime import date
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, Level
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from fees.models import FeeItem, FeeStructure, Payment, Receipt
from fees.services import apply_fee_structure, publish_fee_structure
from schools.models import AcademicYear, Term
from students.tests.factories import create_student, enroll_student, ensure_default_stream


class RecordPaymentViewTests(APITestCase):
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
        self.first_term = Term.objects.create(
            school=self.school,
            academic_year=self.academic_year,
            term=Term.TermChoices.FIRST_TERM,
            start_date=date(2025, 9, 1),
            end_date=date(2025, 12, 15),
            is_active=True,
        )
        self.second_term = Term.objects.create(
            school=self.school,
            academic_year=self.academic_year,
            term=Term.TermChoices.SECOND_TERM,
            start_date=date(2025, 12, 16),
            end_date=date(2026, 4, 1),
        )
        self.level = Level.objects.create(
            school=self.school,
            name='Junior High',
            is_system_generated=False,
        )
        self.class_level = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='JHS 1',
            is_system_generated=False,
        )
        self.stream = ensure_default_stream(self.class_level)
        self.student = create_student(
            school=self.school,
            student_id='TA-0001',
            first_name='Ama',
            last_name='Mensah',
        )
        enroll_student(
            student=self.student,
            term=self.first_term,
            stream=self.stream,
            is_new_student=True,
        )

    def _apply_tuition(self, *, term, amount=Decimal('500.00')):
        structure = FeeStructure.objects.create(
            school=self.school,
            term=term,
            created_by=self.user,
        )
        FeeItem.objects.create(
            fee_structure=structure,
            name='Tuition Fee',
            amount=amount,
            applies_to_type=FeeItem.AppliesToType.SCHOOL,
            student_type=FeeItem.StudentType.ALL_STUDENTS,
        )
        publish_fee_structure(structure)
        apply_fee_structure(structure)

    def test_payment_target_returns_earliest_outstanding_term(self):
        self._apply_tuition(term=self.first_term, amount=Decimal('500.00'))
        self._apply_tuition(term=self.second_term, amount=Decimal('400.00'))
        Payment.objects.create(
            student=self.student,
            term=self.first_term,
            amount=Decimal('100.00'),
            payment_method=Payment.PaymentMethod.CASH,
            recorded_by=self.user,
        )

        url = reverse('student-payment-target', kwargs={'student_id': self.student.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['has_outstanding'])
        self.assertEqual(response.data['target_term']['term'], 'first_term')
        self.assertEqual(Decimal(response.data['outstanding_balance']), Decimal('400.00'))

    def test_record_payment_creates_payment_and_receipt(self):
        self._apply_tuition(term=self.first_term, amount=Decimal('500.00'))
        url = reverse('record-payment')
        paid_at = timezone.now().isoformat()
        response = self.client.post(
            url,
            {
                'student_id': str(self.student.id),
                'amount': '250.00',
                'payment_method': 'cash',
                'paid_at': paid_at,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Receipt.objects.filter(payment__student=self.student).exists())
        self.assertEqual(Payment.objects.filter(student=self.student).count(), 1)
        self.assertEqual(Decimal(response.data['outstanding_after']), Decimal('250.00'))

    def test_record_payment_allows_excess_amount(self):
        self._apply_tuition(term=self.first_term, amount=Decimal('500.00'))
        url = reverse('record-payment')
        response = self.client.post(
            url,
            {
                'student_id': str(self.student.id),
                'amount': '700.00',
                'payment_method': 'mobile_money',
                'paid_at': timezone.now().isoformat(),
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(response.data['outstanding_after']), Decimal('0.00'))
        self.assertEqual(Decimal(response.data['amount_applied']), Decimal('500.00'))
        self.assertEqual(Decimal(response.data['advance_created']), Decimal('200.00'))
        self.assertEqual(Decimal(response.data['advance_balance']), Decimal('200.00'))

    def test_advance_applies_when_next_term_fees_applied(self):
        self._apply_tuition(term=self.first_term, amount=Decimal('500.00'))
        record_url = reverse('record-payment')
        self.client.post(
            record_url,
            {
                'student_id': str(self.student.id),
                'amount': '700.00',
                'payment_method': 'cash',
                'paid_at': timezone.now().isoformat(),
            },
            format='json',
        )

        enroll_student(
            student=self.student,
            term=self.second_term,
            stream=self.stream,
            is_new_student=False,
        )
        self._apply_tuition(term=self.second_term, amount=Decimal('400.00'))

        target_url = reverse('student-payment-target', kwargs={'student_id': self.student.id})
        target = self.client.get(target_url)
        self.assertEqual(target.status_code, status.HTTP_200_OK)
        # 400 billed - 200 advance applied = 200 still owing on second term
        self.assertEqual(Decimal(target.data['outstanding_balance']), Decimal('200.00'))
        self.assertEqual(Decimal(target.data['advance_balance']), Decimal('0.00'))
        self.assertFalse(target.data['has_advance'])
        self.assertEqual(
            Payment.objects.filter(
                student=self.student,
                term=self.second_term,
                payment_method=Payment.PaymentMethod.ADVANCE_CREDIT,
            ).count(),
            1,
        )