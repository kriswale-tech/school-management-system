from datetime import date, timedelta
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, Level
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from fees.models import FeeItem, FeeStructure
from schools.models import AcademicYear, SchoolSetup, Term
from schools.tests.factories import create_school_setup


class SetupFeesViewTests(APITestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        set_client_auth_cookies(self.client, self.user)
        self.school = user_school(self.user)
        today = date.today()
        self.academic_year = AcademicYear.objects.create(
            school=self.school,
            academic_year='2025/2026',
            start_date=today - timedelta(days=30),
            end_date=today + timedelta(days=300),
            is_active=True,
        )
        self.term = Term.objects.create(
            school=self.school,
            academic_year=self.academic_year,
            term=Term.TermChoices.FIRST_TERM,
            start_date=today - timedelta(days=20),
            end_date=today + timedelta(days=80),
            is_active=True,
        )
        create_school_setup(
            self.school,
            completed_steps=[
                SchoolSetup.SetupStep.SCHOOL_PROFILE,
                SchoolSetup.SetupStep.ACADEMIC_YEAR_TERM,
                SchoolSetup.SetupStep.CLASSES_AND_SUBJECTS,
                SchoolSetup.SetupStep.ASSESSMENT,
            ],
            current_step=SchoolSetup.SetupStep.FEES,
        )
        self.url = reverse('school-setup-fees')
        self.complete_url = reverse('school-setup-fees-complete')

    def test_get_creates_draft_structure_and_returns_fee_items(self):
        structure = FeeStructure.objects.create(
            school=self.school,
            term=self.term,
            created_by=self.user,
        )
        FeeItem.objects.create(
            fee_structure=structure,
            name='Tuition Fee',
            amount=Decimal('5000.00'),
            applies_to_type=FeeItem.AppliesToType.SCHOOL,
            student_type=FeeItem.StudentType.ALL_STUDENTS,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['fee_structure']['term_id'], str(self.term.id))
        self.assertEqual(len(response.data['fee_items']), 1)
        item = response.data['fee_items'][0]
        self.assertEqual(item['name'], 'Tuition Fee')
        self.assertEqual(item['amount'], '5000.00')
        self.assertEqual(item['applies_to_type'], 'school')
        self.assertEqual(item['applies_to_type_display'], 'School')
        self.assertEqual(item['applies_to_name'], 'Entire School')
        self.assertEqual(item['student_type'], 'all_students')
        self.assertEqual(item['student_type_display'], 'All Students')

    def test_post_creates_fee_item_on_active_term_structure(self):
        response = self.client.post(
            reverse('school-setup-fee-items'),
            {
                'name': 'Tuition Fee',
                'amount': '5000.00',
                'applies_to_type': FeeItem.AppliesToType.SCHOOL,
                'student_type': FeeItem.StudentType.ALL_STUDENTS,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Tuition Fee')
        self.assertEqual(response.data['applies_to_name'], 'Entire School')
        self.assertEqual(FeeItem.objects.count(), 1)
        self.assertEqual(FeeStructure.objects.count(), 1)

    def test_patch_updates_fee_item(self):
        structure = FeeStructure.objects.create(
            school=self.school,
            term=self.term,
            created_by=self.user,
        )
        fee_item = FeeItem.objects.create(
            fee_structure=structure,
            name='PTA Levy',
            amount=Decimal('150.00'),
            applies_to_type=FeeItem.AppliesToType.SCHOOL,
            student_type=FeeItem.StudentType.ALL_STUDENTS,
        )
        level = Level.objects.create(
            school=self.school,
            name='Junior High',
            is_system_generated=False,
        )

        response = self.client.patch(
            reverse('school-setup-fee-item-detail', kwargs={'fee_item_id': fee_item.id}),
            {
                'name': 'Updated PTA Levy',
                'amount': '200.00',
                'applies_to_type': FeeItem.AppliesToType.LEVEL,
                'applies_to_id': str(level.id),
                'student_type': FeeItem.StudentType.CONTINUING_STUDENT,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated PTA Levy')
        self.assertEqual(response.data['amount'], '200.00')
        self.assertEqual(response.data['applies_to_name'], 'Junior High')
        self.assertEqual(response.data['student_type_display'], 'Continuing Student')

    def test_delete_removes_fee_item(self):
        structure = FeeStructure.objects.create(
            school=self.school,
            term=self.term,
            created_by=self.user,
        )
        fee_item = FeeItem.objects.create(
            fee_structure=structure,
            name='ICT Fee',
            amount=Decimal('300.00'),
            applies_to_type=FeeItem.AppliesToType.SCHOOL,
            student_type=FeeItem.StudentType.ALL_STUDENTS,
        )

        response = self.client.delete(
            reverse('school-setup-fee-item-detail', kwargs={'fee_item_id': fee_item.id}),
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(FeeItem.objects.filter(id=fee_item.id).exists())

    def test_complete_advances_setup(self):
        structure = FeeStructure.objects.create(
            school=self.school,
            term=self.term,
            created_by=self.user,
        )
        FeeItem.objects.create(
            fee_structure=structure,
            name='Tuition Fee',
            amount=Decimal('5000.00'),
            applies_to_type=FeeItem.AppliesToType.SCHOOL,
            student_type=FeeItem.StudentType.ALL_STUDENTS,
        )

        response = self.client.post(self.complete_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['next_step'], 'teachers')
        self.assertIn('fees', response.data['completed_steps'])


class AcademicsLookupViewTests(APITestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        set_client_auth_cookies(self.client, self.user)
        self.school = user_school(self.user)
        self.level = Level.objects.create(
            school=self.school,
            name='Primary',
            order=1,
            is_system_generated=False,
        )
        self.inactive_level = Level.objects.create(
            school=self.school,
            name='Inactive Level',
            order=2,
            is_active=False,
            is_system_generated=False,
        )
        self.class_level = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='Basic 4',
            order=1,
            is_system_generated=False,
        )
        ClassLevel.objects.create(
            school=self.school,
            level=self.inactive_level,
            name='Hidden Class',
            order=1,
            is_system_generated=False,
        )

    def test_levels_list_returns_active_levels_only(self):
        response = self.client.get(reverse('academics-levels'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Primary')

    def test_class_levels_list_returns_active_classes_only(self):
        response = self.client.get(reverse('academics-class-levels'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Basic 4')
        self.assertEqual(response.data[0]['level_name'], 'Primary')
