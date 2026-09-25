from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, Level
from accounts.models import User
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from assessments.models import StudentResult
from assessments.services.admin_overview import list_admin_assessment_overview
from schools.models import AcademicYear, Term
from students.tests.factories import create_student, enroll_student, ensure_default_stream
from teachers.models import ClassTeacher


class AdminAssessmentOverviewApiTests(APITestCase):
    def setUp(self):
        self.admin = create_user(is_active=True)
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
            name='JHS',
            is_system_generated=False,
        )
        self.class_a = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='JHS 1',
            is_system_generated=False,
        )
        self.class_b = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='JHS 2',
            is_system_generated=False,
        )
        self.stream_a = ensure_default_stream(self.class_a)
        self.stream_b = ensure_default_stream(self.class_b)

        self.teacher = create_user(
            is_active=True,
            phone_number='+233200000201',
            email='ct@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
            first_name='Class',
            last_name='Teacher',
        )
        ClassTeacher.objects.create(
            teacher=self.teacher,
            class_level=self.class_a,
            stream=self.stream_a,
            term=self.term,
        )

        self.student_a = create_student(
            school=self.school,
            student_id='STU-A01',
            first_name='Ama',
            last_name='Ready',
        )
        self.student_b = create_student(
            school=self.school,
            student_id='STU-B01',
            first_name='Kofi',
            last_name='Pending',
        )
        enroll_student(student=self.student_a, term=self.term, stream=self.stream_a)
        enroll_student(student=self.student_b, term=self.term, stream=self.stream_b)

        StudentResult.objects.create(
            student=self.student_a,
            term=self.term,
            class_level=self.class_a,
            stream=self.stream_a,
            status=StudentResult.Status.APPROVED,
        )

        self.url = reverse('academics-assessments-admin-classes')

    def test_list_defaults_to_classes_waiting_on_admin(self):
        response = self.client.get(self.url, {'term_id': str(self.term.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['stream_id'], str(self.stream_a.id))
        self.assertEqual(response.data['ready_for_you_count'], 1)
        self.assertEqual(response.data['with_class_teacher_count'], 1)
        self.assertEqual(response.data['filtered_students_count'], 1)
        self.assertIn('page', response.data)
        self.assertIn('total_pages', response.data)

    def test_status_and_search_filters(self):
        pending = self.client.get(
            self.url,
            {'term_id': str(self.term.id), 'status': 'with_class_teacher'},
        )
        self.assertEqual(pending.status_code, status.HTTP_200_OK)
        self.assertEqual(pending.data['count'], 1)
        self.assertEqual(pending.data['results'][0]['stream_id'], str(self.stream_b.id))
        self.assertEqual(pending.data['filtered_students_count'], 1)

        search = self.client.get(
            self.url,
            {'term_id': str(self.term.id), 'search': 'Teacher'},
        )
        self.assertEqual(search.status_code, status.HTTP_200_OK)
        self.assertEqual(search.data['count'], 1)
        self.assertEqual(search.data['results'][0]['stream_id'], str(self.stream_a.id))

    def test_invalid_status_returns_400(self):
        response = self.client.get(
            self.url,
            {'term_id': str(self.term.id), 'status': 'nope'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_dashboard_path_keeps_all_rows(self):
        payload = list_admin_assessment_overview(
            school=self.school,
            term_id=self.term.id,
        )
        self.assertEqual(len(payload['results']), 2)
