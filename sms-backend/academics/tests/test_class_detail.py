from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import (
    ClassLevel,
    ClassStream,
    ClassSubject,
    Level,
    LevelSubject,
    Subject,
    SubjectGroup,
)
from accounts.models import User
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from schools.models import AcademicYear, Term
from students.tests.factories import create_student, enroll_student, ensure_default_stream
from teachers.models import ClassTeacher, TeachingAssignment


class ClassDetailEndpointsTests(APITestCase):
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
            name='Lower Primary',
            is_system_generated=False,
        )
        self.class_level = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='Primary 1',
            is_system_generated=False,
        )
        ensure_default_stream(self.class_level)
        self.stream = ClassStream.objects.create(
            class_level=self.class_level,
            name='A',
            is_default=False,
        )

        self.math = Subject.objects.create(
            school=self.school,
            name='Mathematics',
            is_system_generated=False,
        )
        self.language = Subject.objects.create(
            school=self.school,
            name='Ghanaian Language',
            is_system_generated=False,
        )
        for subject in (self.math, self.language):
            LevelSubject.objects.create(
                school=self.school,
                level=self.level,
                subject=subject,
                is_system_generated=False,
            )

        self.math_class_subject = ClassSubject.objects.create(
            school=self.school,
            class_level=self.class_level,
            subject=self.math,
            is_system_generated=False,
        )
        self.language_class_subject = ClassSubject.objects.create(
            school=self.school,
            class_level=self.class_level,
            subject=self.language,
            is_system_generated=False,
        )
        self.group_twi = SubjectGroup.objects.create(
            class_subject=self.language_class_subject,
            name='Twi',
        )
        self.group_ga = SubjectGroup.objects.create(
            class_subject=self.language_class_subject,
            name='Ga',
        )

        self.student = create_student(
            school=self.school,
            student_id='P1-001',
            first_name='Ada',
            last_name='Mensah',
            admission_date=date(2025, 9, 1),
        )
        enroll_student(student=self.student, term=self.term, stream=self.stream)

        self.teacher = create_user(
            is_active=True,
            first_name='Jane',
            last_name='Doe',
            phone_number='+233200000099',
            email='jane@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
        )

        self.detail_url = reverse('academics-class-detail', args=[self.stream.id])
        self.students_url = reverse('academics-class-students', args=[self.stream.id])
        self.subjects_url = reverse('academics-class-subjects', args=[self.stream.id])
        self.teachers_url = reverse('academics-classes-teachers')
        self.class_teacher_url = reverse(
            'academics-class-teacher-assign',
            args=[self.stream.id],
        )
        self.subject_teacher_url = reverse(
            'academics-class-subject-teacher-assign',
            args=[self.stream.id],
        )

    def test_class_detail(self):
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Primary 1 A')
        self.assertEqual(response.data['level_name'], 'Lower Primary')
        self.assertEqual(response.data['students_count'], 1)
        self.assertEqual(response.data['subjects_count'], 3)
        self.assertEqual(response.data['unassigned_subjects_count'], 3)
        self.assertTrue(response.data['needs_attention'])
        self.assertIsNone(response.data['class_teacher'])

    def test_class_students(self):
        response = self.client.get(self.students_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        student = response.data['results'][0]
        self.assertEqual(student['full_name'], 'Ada Mensah')
        self.assertEqual(student['student_id'], 'P1-001')
        self.assertEqual(student['admission_date'], '2025-09-01')

    def test_class_subjects_flattens_groups(self):
        response = self.client.get(self.subjects_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        by_name = {item['name']: item for item in response.data['results']}
        self.assertEqual(
            set(by_name),
            {'Mathematics', 'Ghanaian Language (Ga)', 'Ghanaian Language (Twi)'},
        )
        self.assertEqual(by_name['Mathematics']['kind'], 'class_subject')
        self.assertEqual(by_name['Ghanaian Language (Twi)']['kind'], 'subject_group')
        self.assertEqual(
            str(by_name['Ghanaian Language (Twi)']['subject_group_id']),
            str(self.group_twi.id),
        )
        self.assertEqual(by_name['Mathematics']['students_count'], 1)

    def test_assign_class_teacher(self):
        response = self.client.put(
            self.class_teacher_url,
            {'teacher_id': str(self.teacher.id)},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['class_teacher']['full_name'], 'Jane Doe')
        self.assertTrue(
            ClassTeacher.objects.filter(
                teacher=self.teacher,
                stream=self.stream,
                term=self.term,
            ).exists(),
        )

    def test_assign_class_teacher_replaces_whole_class_assignment(self):
        ClassTeacher.objects.create(
            teacher=self.teacher,
            class_level=self.class_level,
            stream=None,
            term=self.term,
        )

        response = self.client.put(
            self.class_teacher_url,
            {'teacher_id': str(self.teacher.id)},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            ClassTeacher.objects.filter(
                teacher=self.teacher,
                class_level=self.class_level,
                term=self.term,
            ).count(),
            1,
        )
        self.assertTrue(
            ClassTeacher.objects.filter(
                teacher=self.teacher,
                stream=self.stream,
                term=self.term,
            ).exists(),
        )
        self.assertFalse(
            ClassTeacher.objects.filter(
                teacher=self.teacher,
                class_level=self.class_level,
                stream__isnull=True,
                term=self.term,
            ).exists(),
        )

    def test_assign_subject_teacher_for_group(self):
        response = self.client.put(
            self.subject_teacher_url,
            {
                'teacher_id': str(self.teacher.id),
                'class_subject_id': str(self.language_class_subject.id),
                'subject_group_id': str(self.group_twi.id),
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        by_name = {item['name']: item for item in response.data['results']}
        self.assertEqual(
            by_name['Ghanaian Language (Twi)']['teacher']['full_name'],
            'Jane Doe',
        )
        self.assertIsNone(by_name['Ghanaian Language (Ga)']['teacher'])
        self.assertTrue(
            TeachingAssignment.objects.filter(
                teacher=self.teacher,
                subject_group=self.group_twi,
                term=self.term,
            ).exists(),
        )

    def test_teacher_options_include_summaries(self):
        ClassTeacher.objects.create(
            teacher=self.teacher,
            class_level=self.class_level,
            stream=self.stream,
            term=self.term,
        )
        TeachingAssignment.objects.create(
            teacher=self.teacher,
            class_subject=self.math_class_subject,
            stream=self.stream,
            term=self.term,
        )

        response = self.client.get(self.teachers_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        teacher = next(
            item for item in response.data['results'] if item['full_name'] == 'Jane Doe'
        )
        self.assertIn('Primary 1 A', teacher['class_teacher_summary'])
        self.assertIn('Mathematics', teacher['teaching_summary'])
