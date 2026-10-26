from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, Level
from accounts.models import User
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from activities.models import Activity
from activities.services import record_activity
from schools.models import AcademicYear, Term
from students.tests.factories import create_student, enroll_student, ensure_default_stream


class StaffDashboardViewTests(APITestCase):
    def setUp(self):
        self.admin = create_user(is_active=True, role=User.RoleChoices.ADMIN)
        self.school = user_school(self.admin)
        self.staff = create_user(
            is_active=True,
            role=User.RoleChoices.STAFF,
            school=self.school,
            phone_number='+233201111120',
            email='staff-dash@test.com',
            first_name='Abena',
        )
        set_client_auth_cookies(self.client, self.staff)
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
        self.url = reverse('dashboard-staff')

    def test_staff_can_load_dashboard(self):
        create_user(
            is_active=True,
            role=User.RoleChoices.TEACHER,
            school=self.school,
            phone_number='+233201111121',
            email='teacher-dash@test.com',
        )
        student = create_student(school=self.school, first_name='Ama', last_name='Mensah')
        enroll_student(
            student=student,
            term=self.term,
            class_level=self.class_level,
            stream=self.stream,
            is_new_student=True,
        )
        record_activity(
            school=self.school,
            verb=Activity.Verb.STUDENT_ENROLLED,
            summary='Ama Mensah enrolled in Primary 1',
            actor=self.staff,
            term=self.term,
            stream=self.stream,
            href='/students',
        )
        record_activity(
            school=self.school,
            verb=Activity.Verb.PAYMENT_RECORDED,
            summary='Payment recorded for Ama Mensah',
            actor=self.admin,
            term=self.term,
            href='/fees',
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['school_overview']['total_students'], 1)
        self.assertEqual(response.data['school_overview']['teachers_count'], 1)
        self.assertNotIn('fees_overview', response.data)
        self.assertFalse(
            any(item['code'] == 'debtors' for item in response.data['needs_attention']),
        )
        summaries = [row['summary'] for row in response.data['activities']]
        self.assertTrue(any('enrolled' in summary for summary in summaries))
        self.assertFalse(any('Payment' in summary for summary in summaries))

    def test_admin_cannot_access_staff_dashboard(self):
        set_client_auth_cookies(self.client, self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
