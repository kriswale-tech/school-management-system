from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import (
    ClassLevel,
    ClassSubject,
    Level,
    LevelSubject,
    Subject,
)
from accounts.models import User
from accounts.tests.factories import (
    create_user,
    set_client_auth_cookies,
    user_school,
)
from schools.models import AcademicYear, Term
from students.tests.factories import create_student, enroll_student, ensure_default_stream
from teachers.models import TeachingAssignment


class TeachingAssignmentViewsTests(APITestCase):
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
            name='Primary',
            is_system_generated=False,
        )
        self.class_level = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='Primary 1',
            is_system_generated=False,
        )
        self.stream = ensure_default_stream(self.class_level)
        self.subject = Subject.objects.create(
            school=self.school,
            name='Mathematics',
            is_system_generated=False,
        )
        LevelSubject.objects.create(
            school=self.school,
            level=self.level,
            subject=self.subject,
            is_system_generated=False,
        )
        self.class_subject = ClassSubject.objects.create(
            school=self.school,
            class_level=self.class_level,
            subject=self.subject,
            is_system_generated=False,
        )
        self.teacher = create_user(
            is_active=True,
            phone_number='+233200000022',
            email='subj@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
            first_name='Sub',
            last_name='Teacher',
        )
        self.assignment = TeachingAssignment.objects.create(
            teacher=self.teacher,
            class_subject=self.class_subject,
            stream=self.stream,
            term=self.term,
        )
        self.student = create_student(
            school=self.school,
            student_id='S-1',
            first_name='Ada',
        )
        enroll_student(student=self.student, term=self.term, stream=self.stream)

        self.detail_url = reverse(
            'academics-teaching-assignment-detail',
            kwargs={'assignment_id': self.assignment.id},
        )
        self.students_url = reverse(
            'academics-teaching-assignment-students',
            kwargs={'assignment_id': self.assignment.id},
        )
        self.assign_url = reverse(
            'academics-class-teacher-assign',
            kwargs={'stream_id': self.stream.id},
        )

    def test_teacher_can_view_own_subject_and_students(self):
        set_client_auth_cookies(self.client, self.teacher)

        detail = self.client.get(self.detail_url)
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data['subject_label'], 'Mathematics')
        self.assertEqual(detail.data['students_count'], 1)

        students = self.client.get(self.students_url)
        self.assertEqual(students.status_code, status.HTTP_200_OK)
        self.assertEqual(len(students.data['results']), 1)
        self.assertEqual(students.data['results'][0]['full_name'], 'Ada Mensah')

    def test_other_teacher_cannot_view_assignment(self):
        other = create_user(
            is_active=True,
            phone_number='+233200000023',
            email='other@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
            first_name='Other',
            last_name='Teacher',
        )
        set_client_auth_cookies(self.client, other)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_cannot_assign_class_teacher(self):
        set_client_auth_cookies(self.client, self.teacher)
        response = self.client.put(
            self.assign_url,
            {'teacher_id': str(self.teacher.id)},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
