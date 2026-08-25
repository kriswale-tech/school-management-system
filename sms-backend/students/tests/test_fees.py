from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, Level
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from fees.models import FeeItem, FeeStructure, Payment
from fees.services import apply_fee_structure, publish_fee_structure
from schools.models import AcademicYear, Term
from students.tests.factories import create_student, enroll_student, ensure_default_stream


class StudentFeesViewTests(APITestCase):
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
        self.prior_year = AcademicYear.objects.create(
            school=self.school,
            academic_year='2024/2025',
            start_date=date(2024, 9, 1),
            end_date=date(2025, 7, 31),
            is_active=False,
        )
        self.prior_term = Term.objects.create(
            school=self.school,
            academic_year=self.prior_year,
            term=Term.TermChoices.FIRST_TERM,
            start_date=date(2024, 9, 1),
            end_date=date(2024, 12, 15),
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
        return structure

    def test_current_year_fees_empty(self):
        url = reverse('student-current-year-fees', kwargs={'student_id': self.student.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['academic_year'], '2025/2026')
        self.assertEqual(response.data['payment_status'], 'no_fees')
        self.assertEqual(Decimal(response.data['total_billed']), Decimal('0.00'))
        self.assertEqual(len(response.data['terms']), 2)

    def test_current_year_fees_with_billing_and_payment(self):
        self._apply_tuition(term=self.first_term, amount=Decimal('500.00'))
        Payment.objects.create(
            student=self.student,
            term=self.first_term,
            amount=Decimal('200.00'),
            payment_method=Payment.PaymentMethod.CASH,
            recorded_by=self.user,
        )

        url = reverse('student-current-year-fees', kwargs={'student_id': self.student.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data['total_billed']), Decimal('500.00'))
        self.assertEqual(Decimal(response.data['total_paid']), Decimal('200.00'))
        self.assertEqual(response.data['payment_status'], 'partially_paid')

        first = next(t for t in response.data['terms'] if t['term'] == 'first_term')
        self.assertEqual(first['term_name'], 'First Term')
        self.assertEqual(len(first['fee_items']), 1)
        self.assertEqual(first['fee_items'][0]['name'], 'Tuition Fee')

    def test_fee_history_years_with_data_only(self):
        self._apply_tuition(term=self.first_term)
        enroll_student(
            student=self.student,
            term=self.prior_term,
            stream=self.stream,
            is_new_student=False,
        )
        self._apply_tuition(term=self.prior_term, amount=Decimal('300.00'))

        url = reverse('student-fee-history', kwargs={'student_id': self.student.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        years = response.data['years']
        self.assertEqual(len(years), 2)
        self.assertEqual(years[0]['academic_year'], '2025/2026')
        self.assertEqual(years[1]['academic_year'], '2024/2025')

        filtered = self.client.get(url, {'academic_year': str(self.prior_year.id)})
        self.assertEqual(filtered.status_code, status.HTTP_200_OK)
        self.assertEqual(len(filtered.data['years']), 1)
        self.assertEqual(filtered.data['years'][0]['academic_year'], '2024/2025')

    def test_fees_accept_term_filter(self):
        self._apply_tuition(term=self.first_term, amount=Decimal('500.00'))
        self._apply_tuition(term=self.second_term, amount=Decimal('400.00'))

        url = reverse('student-current-year-fees', kwargs={'student_id': self.student.id})
        response = self.client.get(url, {'term': str(self.first_term.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['terms']), 1)
        self.assertEqual(response.data['terms'][0]['term'], 'first_term')
        self.assertEqual(Decimal(response.data['total_billed']), Decimal('500.00'))

    def test_payment_list_returns_ledger_rows(self):
        self._apply_tuition(term=self.first_term, amount=Decimal('500.00'))
        Payment.objects.create(
            student=self.student,
            term=self.first_term,
            amount=Decimal('150.00'),
            payment_method=Payment.PaymentMethod.MOBILE_MONEY,
            recorded_by=self.user,
        )

        url = reverse('student-payment-list', kwargs={'student_id': self.student.id})
        response = self.client.get(url, {'term': str(self.first_term.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['payment_method'], 'mobile_money')
        self.assertEqual(Decimal(response.data[0]['amount']), Decimal('150.00'))
        self.assertEqual(response.data[0]['term_name'], 'First Term')
        self.assertIsNone(response.data[0]['receipt'])
