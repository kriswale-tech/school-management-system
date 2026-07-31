from datetime import date
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, ClassStream, Level
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from fees.models import FeeItem, FeeStructure, Payment, StudentFee
from fees.services import apply_fee_structure, publish_fee_structure
from schools.models import AcademicYear, Term
from students.models import Parent, Student, StudentParent
from students.tests.factories import create_student, enroll_student, ensure_default_stream


class StudentViewTests(APITestCase):
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
        self.level = Level.objects.create(
            school=self.school,
            name='Junior High',
            is_system_generated=False,
        )
        self.class_level_a = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='JHS 1',
            is_system_generated=False,
        )
        self.class_level_b = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='JHS 2',
            is_system_generated=False,
        )
        self.default_stream_a = ensure_default_stream(self.class_level_a)
        self.named_stream_a = ClassStream.objects.create(
            class_level=self.class_level_a,
            name='A',
            is_default=False,
        )
        self.default_stream_b = ensure_default_stream(self.class_level_b)

        self.student_a = create_student(
            school=self.school,
            student_id='STU-001',
            first_name='Ama',
            last_name='Mensah',
            gender=Student.GenderChoices.FEMALE,
        )
        self.student_b = create_student(
            school=self.school,
            student_id='STU-002',
            first_name='Kofi',
            last_name='Boateng',
            gender=Student.GenderChoices.MALE,
        )
        enroll_student(
            student=self.student_a,
            term=self.term,
            stream=self.named_stream_a,
            is_new_student=True,
        )
        enroll_student(
            student=self.student_b,
            term=self.term,
            stream=self.default_stream_b,
            is_new_student=False,
        )

        self.parent = Parent.objects.create(
            school=self.school,
            name='Akosua Mensah',
            phone_number='0244111222',
        )
        StudentParent.objects.create(
            student=self.student_a,
            parent=self.parent,
            relationship=StudentParent.RelationshipChoices.MOTHER,
            is_primary=True,
        )

        self.list_url = reverse('student-list')
        self.stats_url = reverse('student-stats')

    def test_list_returns_students_for_active_term(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        student_ids = {item['student_id'] for item in response.data['results']}
        self.assertEqual(student_ids, {'STU-001', 'STU-002'})

        ama = next(
            item for item in response.data['results'] if item['student_id'] == 'STU-001'
        )
        self.assertEqual(ama['class_level']['name'], 'JHS 1')
        self.assertEqual(ama['stream']['name'], 'A')
        self.assertEqual(ama['stream']['full_name'], 'JHS 1 A')
        self.assertFalse(ama['stream']['is_default'])
        self.assertTrue(ama['is_new_student'])
        self.assertEqual(ama['primary_parent']['name'], 'Akosua Mensah')
        self.assertEqual(ama['primary_parent']['phone_number'], '0244111222')
        self.assertEqual(ama['primary_parent']['phone_number_alt'], '')
        self.assertEqual(ama['primary_parent']['email'], '')
        self.assertEqual(ama['primary_parent']['relationship'], 'mother')

        kofi = next(
            item for item in response.data['results'] if item['student_id'] == 'STU-002'
        )
        self.assertIsNone(kofi['stream']['name'])
        self.assertTrue(kofi['stream']['is_default'])
        self.assertIsNone(kofi['primary_parent'])

    def test_list_search_by_student_id_and_name(self):
        response = self.client.get(self.list_url, {'search': 'STU-002'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['first_name'], 'Kofi')

        response = self.client.get(self.list_url, {'search': 'Mensah'})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['student_id'], 'STU-001')

    def test_list_filter_by_class_level_and_stream(self):
        response = self.client.get(
            self.list_url,
            {'class_level': str(self.class_level_a.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['student_id'], 'STU-001')

        response = self.client.get(
            self.list_url,
            {'stream': str(self.named_stream_a.id)},
        )
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['student_id'], 'STU-001')

        response = self.client.get(
            self.list_url,
            {'stream': str(self.default_stream_a.id)},
        )
        self.assertEqual(response.data['count'], 0)

    def test_stats_returns_summary_counts(self):
        structure = FeeStructure.objects.create(
            school=self.school,
            term=self.term,
            created_by=self.user,
        )
        FeeItem.objects.create(
            fee_structure=structure,
            name='Tuition',
            amount=Decimal('500.00'),
            applies_to_type=FeeItem.AppliesToType.SCHOOL,
            student_type=FeeItem.StudentType.ALL_STUDENTS,
        )
        publish_fee_structure(structure)
        apply_fee_structure(structure)

        StudentFee.objects.filter(student=self.student_a).update(amount=Decimal('500.00'))
        Payment.objects.create(
            student=self.student_a,
            term=self.term,
            amount=Decimal('500.00'),
            payment_method=Payment.PaymentMethod.CASH,
            paid_at=timezone.now(),
            recorded_by=self.user,
        )

        response = self.client.get(self.stats_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_students'], 2)
        self.assertEqual(response.data['new_students'], 1)
        self.assertEqual(response.data['continuing_students'], 1)
        self.assertEqual(response.data['boys'], 1)
        self.assertEqual(response.data['girls'], 1)
        self.assertEqual(response.data['fully_paid'], 1)
        self.assertEqual(response.data['owing'], 1)

    def test_list_requires_active_term(self):
        self.term.is_active = False
        self.term.save(update_fields=['is_active'])

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
