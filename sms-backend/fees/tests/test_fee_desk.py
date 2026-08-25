from datetime import date
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, Level
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from fees.models import FeeItem, FeeStructure, Payment
from fees.services import apply_fee_structure, publish_fee_structure
from schools.models import AcademicYear, Term
from students.tests.factories import create_student, enroll_student, ensure_default_stream


class FeeDeskViewTests(APITestCase):
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
        self.other_class = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='JHS 2',
            is_system_generated=False,
        )
        self.stream = ensure_default_stream(self.class_level)
        self.other_stream = ensure_default_stream(self.other_class)

        self.student_a = create_student(
            school=self.school,
            student_id='TA-0001',
            first_name='Ama',
            last_name='Mensah',
        )
        self.student_b = create_student(
            school=self.school,
            student_id='TA-0002',
            first_name='Kofi',
            last_name='Owusu',
        )
        enroll_student(
            student=self.student_a,
            term=self.first_term,
            stream=self.stream,
            is_new_student=True,
        )
        enroll_student(
            student=self.student_b,
            term=self.first_term,
            stream=self.other_stream,
            is_new_student=True,
        )

    def _apply_tuition(self, *, amount=Decimal('500.00')):
        structure = FeeStructure.objects.create(
            school=self.school,
            term=self.first_term,
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

    def test_filter_options_include_active_term(self):
        url = reverse('fee-desk-filter-options')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['active_term_id'], str(self.first_term.id))
        self.assertEqual(len(response.data['terms']), 2)
        active = next(term for term in response.data['terms'] if term['is_active'])
        self.assertEqual(active['id'], str(self.first_term.id))

    def test_list_and_stats_default_to_active_term(self):
        self._apply_tuition()
        paid_at = timezone.now()
        Payment.objects.create(
            student=self.student_a,
            term=self.first_term,
            amount=Decimal('200.00'),
            payment_method=Payment.PaymentMethod.CASH,
            recorded_by=self.user,
            paid_at=paid_at,
        )

        list_response = self.client.get(reverse('fee-desk-list'))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 2)

        ama = next(row for row in list_response.data['results'] if row['student_id'] == 'TA-0001')
        self.assertEqual(Decimal(ama['amount_paid']), Decimal('200.00'))
        self.assertEqual(Decimal(ama['remaining_balance']), Decimal('300.00'))
        self.assertIsNotNone(ama['last_transaction_at'])

        stats_response = self.client.get(reverse('fee-desk-stats'))
        self.assertEqual(stats_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(stats_response.data['total_expected']), Decimal('1000.00'))
        self.assertEqual(Decimal(stats_response.data['total_collected']), Decimal('200.00'))
        self.assertEqual(Decimal(stats_response.data['outstanding']), Decimal('800.00'))
        self.assertEqual(stats_response.data['debtors_count'], 2)
        self.assertEqual(stats_response.data['total_students'], 2)

    def test_filters_affect_list_and_stats(self):
        self._apply_tuition()
        Payment.objects.create(
            student=self.student_a,
            term=self.first_term,
            amount=Decimal('500.00'),
            payment_method=Payment.PaymentMethod.CASH,
            recorded_by=self.user,
        )

        params = {'class_level': str(self.class_level.id), 'search': 'Ama'}
        list_response = self.client.get(reverse('fee-desk-list'), params)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 1)
        self.assertEqual(list_response.data['results'][0]['student_id'], 'TA-0001')

        stats_response = self.client.get(reverse('fee-desk-stats'), params)
        self.assertEqual(stats_response.status_code, status.HTTP_200_OK)
        self.assertEqual(stats_response.data['total_students'], 1)
        self.assertEqual(stats_response.data['debtors_count'], 0)
        self.assertEqual(Decimal(stats_response.data['total_collected']), Decimal('500.00'))
