from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, Level
from accounts.models import User
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from fees.models import FeeItem, FeeStructure
from fees.services import apply_fee_structure, publish_fee_structure
from schools.models import AcademicYear, Term
from students.tests.factories import create_student, enroll_student, ensure_default_stream


class AdminDashboardViewTests(APITestCase):
    def setUp(self):
        self.admin = create_user(is_active=True, role=User.RoleChoices.ADMIN)
        set_client_auth_cookies(self.client, self.admin)
        self.school = user_school(self.admin)
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
            name='Lower Primary',
            is_system_generated=False,
        )
        self.class_level = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='Primary 1',
            is_system_generated=False,
        )
        self.stream = ensure_default_stream(self.class_level)
        self.url = reverse('dashboard-admin')

    def _apply_tuition(self, *, amount=Decimal('500.00')):
        structure = FeeStructure.objects.create(
            school=self.school,
            term=self.term,
            created_by=self.admin,
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

    def test_admin_can_load_dashboard(self):
        student = create_student(school=self.school, first_name='Ama', last_name='Mensah')
        enroll_student(
            student=student,
            term=self.term,
            class_level=self.class_level,
            stream=self.stream,
            is_new_student=True,
        )
        self._apply_tuition()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['school_overview']['total_students'], 1)
        self.assertEqual(response.data['fees_overview']['debtors_count'], 1)
        self.assertEqual(len(response.data['top_debtors']), 1)
        self.assertEqual(response.data['top_debtors'][0]['full_name'], 'Ama Mensah')
        self.assertFalse(response.data['show_academic_widgets'])
        self.assertTrue(
            any(item['code'] == 'debtors' for item in response.data['needs_attention']),
        )

    def test_teacher_cannot_access_admin_dashboard(self):
        teacher = create_user(
            is_active=True,
            role=User.RoleChoices.TEACHER,
            school=self.school,
            phone_number='+233201111111',
            email='teacher@test.com',
        )
        set_client_auth_cookies(self.client, teacher)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
