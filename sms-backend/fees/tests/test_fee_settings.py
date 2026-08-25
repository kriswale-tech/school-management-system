from datetime import date, timedelta
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, Level
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from fees.models import FeeItem, FeeStructure, StudentFee
from fees.services import apply_fee_structure, publish_fee_structure
from schools.models import AcademicYear, Term
from students.tests.factories import create_student, enroll_student, ensure_default_stream


class FeeSettingsViewTests(APITestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        set_client_auth_cookies(self.client, self.user)
        self.school = user_school(self.user)
        today = date.today()
        self.academic_year = AcademicYear.objects.create(
            school=self.school,
            academic_year='2025/2026',
            start_date=today - timedelta(days=200),
            end_date=today + timedelta(days=200),
            is_active=True,
        )
        self.past_term = Term.objects.create(
            school=self.school,
            academic_year=self.academic_year,
            term=Term.TermChoices.FIRST_TERM,
            start_date=today - timedelta(days=180),
            end_date=today - timedelta(days=30),
        )
        self.current_term = Term.objects.create(
            school=self.school,
            academic_year=self.academic_year,
            term=Term.TermChoices.SECOND_TERM,
            start_date=today - timedelta(days=20),
            end_date=today + timedelta(days=60),
            is_active=True,
        )
        self.future_term = Term.objects.create(
            school=self.school,
            academic_year=self.academic_year,
            term=Term.TermChoices.THIRD_TERM,
            start_date=today + timedelta(days=70),
            end_date=today + timedelta(days=150),
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
            student_id='TA-0100',
            first_name='Ama',
            last_name='Mensah',
        )
        enroll_student(
            student=self.student,
            term=self.current_term,
            stream=self.stream,
            is_new_student=True,
        )

    def test_get_creates_structure_for_selected_term(self):
        response = self.client.get(
            reverse('fee-structure-detail'),
            {'term': str(self.future_term.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['fee_structure']['term_id'], str(self.future_term.id))
        self.assertTrue(response.data['fee_structure']['is_editable'])
        self.assertFalse(response.data['fee_structure']['term_ended'])
        self.assertFalse(response.data['fee_structure']['can_apply'])
        self.assertEqual(response.data['fee_items'], [])

    def test_create_item_on_future_term(self):
        response = self.client.post(
            reverse('fee-structure-item-create'),
            {
                'term': str(self.future_term.id),
                'name': 'Tuition Fee',
                'amount': '800.00',
                'applies_to_type': FeeItem.AppliesToType.SCHOOL,
                'student_type': FeeItem.StudentType.ALL_STUDENTS,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Tuition Fee')
        self.assertEqual(response.data['term_id'], str(self.future_term.id))
        structure = FeeStructure.objects.get(term=self.future_term)
        self.assertEqual(structure.fee_items.count(), 1)

    def test_apply_bills_enrolled_students_and_locks_catalog(self):
        create_response = self.client.post(
            reverse('fee-structure-item-create'),
            {
                'name': 'Tuition Fee',
                'amount': '500.00',
                'applies_to_type': FeeItem.AppliesToType.SCHOOL,
                'student_type': FeeItem.StudentType.ALL_STUDENTS,
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        structure = FeeStructure.objects.get(term=self.current_term)

        response = self.client.post(
            reverse('fee-structure-apply', kwargs={'structure_id': structure.id}),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['fee_structure']['status'], 'applied')
        self.assertTrue(response.data['fee_structure']['is_locked'])
        self.assertFalse(response.data['fee_structure']['can_apply'])
        self.assertEqual(StudentFee.objects.filter(student=self.student).count(), 1)

        locked = self.client.post(
            reverse('fee-structure-item-create'),
            {
                'name': 'Extra Levy',
                'amount': '20.00',
                'applies_to_type': FeeItem.AppliesToType.SCHOOL,
            },
            format='json',
        )
        self.assertEqual(locked.status_code, status.HTTP_400_BAD_REQUEST)

    def test_late_join_after_apply_creates_student_fees(self):
        structure = FeeStructure.objects.create(
            school=self.school,
            term=self.current_term,
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

        late = create_student(
            school=self.school,
            student_id='TA-0101',
            first_name='Kofi',
            last_name='Boateng',
        )
        enroll_student(
            student=late,
            term=self.current_term,
            stream=self.stream,
            is_new_student=True,
        )

        self.assertEqual(StudentFee.objects.filter(student=late).count(), 1)

    def test_past_term_without_structure_is_rejected(self):
        response = self.client.get(
            reverse('fee-structure-detail'),
            {'term': str(self.past_term.id)},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        create = self.client.post(
            reverse('fee-structure-item-create'),
            {
                'term': str(self.past_term.id),
                'name': 'Old Fee',
                'amount': '100.00',
                'applies_to_type': FeeItem.AppliesToType.SCHOOL,
            },
            format='json',
        )
        self.assertEqual(create.status_code, status.HTTP_400_BAD_REQUEST)

    def test_past_term_with_structure_is_read_only(self):
        structure = FeeStructure.objects.create(
            school=self.school,
            term=self.past_term,
            created_by=self.user,
        )
        FeeItem.objects.create(
            fee_structure=structure,
            name='Historical Tuition',
            amount=Decimal('400.00'),
            applies_to_type=FeeItem.AppliesToType.SCHOOL,
            student_type=FeeItem.StudentType.ALL_STUDENTS,
        )

        response = self.client.get(
            reverse('fee-structure-detail'),
            {'term': str(self.past_term.id)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['fee_structure']['term_ended'])
        self.assertFalse(response.data['fee_structure']['is_editable'])
        self.assertFalse(response.data['fee_structure']['can_apply'])
        self.assertEqual(len(response.data['fee_items']), 1)

        apply = self.client.post(
            reverse('fee-structure-apply', kwargs={'structure_id': structure.id}),
        )
        self.assertEqual(apply.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_options_mark_ended_terms(self):
        FeeStructure.objects.create(
            school=self.school,
            term=self.past_term,
            created_by=self.user,
        )
        response = self.client.get(reverse('fee-desk-filter-options'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        by_id = {row['id']: row for row in response.data['terms']}
        self.assertTrue(by_id[str(self.past_term.id)]['is_ended'])
        self.assertTrue(by_id[str(self.past_term.id)]['has_fee_structure'])
        self.assertFalse(by_id[str(self.future_term.id)]['is_ended'])
        self.assertFalse(by_id[str(self.future_term.id)]['has_fee_structure'])
