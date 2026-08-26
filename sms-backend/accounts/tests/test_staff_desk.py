from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, Level
from accounts.models import Profile, User
from accounts.tests.factories import (
    create_user,
    set_client_auth_cookies,
    user_school,
)
from schools.models import AcademicYear, Term
from teachers.models import ClassTeacher


class StaffDeskAPITests(APITestCase):
    def setUp(self):
        self.admin = create_user(is_active=True)
        self.school = user_school(self.admin)
        set_client_auth_cookies(self.client, self.admin)

        self.teacher = create_user(
            phone_number='+233244567891',
            email='teacher@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
            is_active=True,
            first_name='Ama',
            last_name='Teacher',
        )
        Profile.objects.create(user=self.teacher, gender='female')

        self.accountant = create_user(
            phone_number='+233244567892',
            email='accountant@test.com',
            school=self.school,
            role=User.RoleChoices.ACCOUNTANT,
            is_active=True,
            first_name='Kojo',
            last_name='Books',
        )

        self.academic_year = AcademicYear.objects.create(
            school=self.school,
            academic_year='2025/2026',
            start_date='2025-09-01',
            end_date='2026-07-31',
            is_active=True,
        )
        self.term = Term.objects.create(
            school=self.school,
            academic_year=self.academic_year,
            term=Term.TermChoices.FIRST_TERM,
            start_date='2025-09-01',
            end_date='2025-12-15',
            is_active=True,
        )
        self.level = Level.objects.create(
            school=self.school,
            name='Primary',
            order=1,
        )
        self.class_level = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='Basic 1',
            order=1,
        )
        ClassTeacher.objects.create(
            teacher=self.teacher,
            class_level=self.class_level,
            term=self.term,
        )

        self.list_url = reverse('staff-desk-list')
        self.stats_url = reverse('staff-desk-stats')

    def test_list_includes_teacher_flags_and_date_added(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        teacher_row = next(row for row in results if row['id'] == str(self.teacher.id))

        self.assertEqual(teacher_row['full_name'], 'Ama Teacher')
        self.assertEqual(teacher_row['role'], User.RoleChoices.TEACHER)
        self.assertTrue(teacher_row['is_class_teacher'])
        self.assertFalse(teacher_row['is_subject_teacher'])
        self.assertEqual(teacher_row['email'], 'teacher@test.com')
        self.assertEqual(teacher_row['phone_number'], '+233244567891')
        self.assertIn('date_added', teacher_row)

    def test_stats_match_filters(self):
        unfiltered = self.client.get(self.stats_url)
        self.assertEqual(unfiltered.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(unfiltered.data['total_staff'], 3)
        self.assertEqual(unfiltered.data['teachers'], 1)
        self.assertEqual(unfiltered.data['accountants'], 1)
        self.assertGreaterEqual(unfiltered.data['admins'], 1)

        filtered = self.client.get(self.stats_url, {'role': 'teacher'})
        self.assertEqual(filtered.status_code, status.HTTP_200_OK)
        self.assertEqual(filtered.data['total_staff'], 1)
        self.assertEqual(filtered.data['teachers'], 1)
        self.assertEqual(filtered.data['accountants'], 0)
        self.assertEqual(filtered.data['admins'], 0)

        searched = self.client.get(self.stats_url, {'search': 'Books'})
        self.assertEqual(searched.status_code, status.HTTP_200_OK)
        self.assertEqual(searched.data['total_staff'], 1)
        self.assertEqual(searched.data['accountants'], 1)

    def test_detail_returns_profile_and_assignments(self):
        url = reverse('staff-desk-detail', kwargs={'pk': self.teacher.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['full_name'], 'Ama Teacher')
        self.assertTrue(response.data['is_class_teacher'])
        self.assertEqual(response.data['profile']['gender'], 'female')
        self.assertEqual(len(response.data['class_teacher_assignments']), 1)
        self.assertEqual(
            response.data['class_teacher_assignments'][0]['class_level_name'],
            'Basic 1',
        )
        self.assertEqual(
            response.data['class_teacher_assignments'][0]['display_name'],
            'Basic 1',
        )
        self.assertEqual(
            response.data['class_teacher_assignments'][0]['students_count'],
            0,
        )
        self.assertEqual(response.data['teaching_assignments'], [])
