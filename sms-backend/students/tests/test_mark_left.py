from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, Level
from accounts.models import User
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from activities.models import Activity
from schools.models import AcademicYear, Term
from students.models import Student
from students.tests.factories import create_student, enroll_student, ensure_default_stream
from teachers.models import ClassTeacher


class MarkStudentLeftTests(APITestCase):
    def setUp(self):
        self.admin = create_user(is_active=True)
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
            name='JHS',
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
            first_name='Kofi',
            last_name='Asante',
        )
        enroll_student(student=self.student, term=self.term, stream=self.stream)

        self.teacher = create_user(
            is_active=True,
            phone_number='+233200000099',
            email='ct@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
            first_name='Class',
            last_name='Teacher',
        )
        ClassTeacher.objects.create(
            teacher=self.teacher,
            class_level=self.class_level,
            stream=self.stream,
            term=self.term,
        )

        self.mark_url = reverse('student-mark-left', kwargs={'student_id': self.student.id})
        self.reactivate_url = reverse(
            'student-reactivate',
            kwargs={'student_id': self.student.id},
        )

    def test_admin_marks_student_left_and_logs_activity(self):
        set_client_auth_cookies(self.client, self.admin)
        response = self.client.post(
            self.mark_url,
            {'reason': 'transfer', 'notes': 'Moved to Tema'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_active'])
        self.assertEqual(response.data['leave_reason'], 'transfer')
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)
        self.assertEqual(self.student.leave_reason, Student.LeaveReason.TRANSFER)

        activity = Activity.objects.filter(
            school=self.school,
            verb=Activity.Verb.STUDENT_LEFT,
            target_id=self.student.id,
        ).first()
        self.assertIsNotNone(activity)
        self.assertIn('Transferred', activity.summary)

    def test_class_teacher_can_mark_own_student(self):
        set_client_auth_cookies(self.client, self.teacher)
        response = self.client.post(
            self.mark_url,
            {'reason': 'dropout'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['leave_reason'], 'dropout')

    def test_subject_teacher_without_class_role_cannot_mark_left(self):
        subject_teacher = create_user(
            is_active=True,
            phone_number='+233200000088',
            email='st@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
        )
        set_client_auth_cookies(self.client, subject_teacher)
        response = self.client.post(
            self.mark_url,
            {'reason': 'other'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_reactivates_student(self):
        set_client_auth_cookies(self.client, self.admin)
        self.client.post(self.mark_url, {'reason': 'other'}, format='json')
        response = self.client.post(self.reactivate_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_active'])
        self.assertIsNone(response.data['leave_reason'])
        self.assertTrue(
            Activity.objects.filter(
                verb=Activity.Verb.STUDENT_REACTIVATED,
                target_id=self.student.id,
            ).exists()
        )

    def test_teacher_cannot_reactivate(self):
        set_client_auth_cookies(self.client, self.admin)
        self.client.post(self.mark_url, {'reason': 'dropout'}, format='json')
        set_client_auth_cookies(self.client, self.teacher)
        response = self.client.post(self.reactivate_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
