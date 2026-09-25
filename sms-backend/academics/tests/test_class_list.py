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
    StudentSubjectGroup,
    Subject,
    SubjectGroup,
)
from accounts.models import User
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from schools.models import AcademicYear, Term
from students.tests.factories import create_student, enroll_student, ensure_default_stream
from teachers.models import ClassTeacher, TeachingAssignment


class ClassListAndStatsViewTests(APITestCase):
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
            name='Kindergarten',
            is_system_generated=False,
        )
        self.class_with_streams = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='Nursery 1',
            is_system_generated=False,
        )
        ensure_default_stream(self.class_with_streams)
        self.stream_a = ClassStream.objects.create(
            class_level=self.class_with_streams,
            name='A',
            is_default=False,
        )
        self.stream_b = ClassStream.objects.create(
            class_level=self.class_with_streams,
            name='B',
            is_default=False,
        )
        self.class_default_only = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='Nursery 2',
            order=2,
            is_system_generated=False,
        )
        self.default_only_stream = ensure_default_stream(self.class_default_only)

        self.subject = Subject.objects.create(
            school=self.school,
            name='Literacy',
            is_system_generated=False,
        )
        LevelSubject.objects.create(
            school=self.school,
            level=self.level,
            subject=self.subject,
            is_system_generated=False,
        )
        ClassSubject.objects.create(
            school=self.school,
            class_level=self.class_with_streams,
            subject=self.subject,
            is_system_generated=False,
        )

        student = create_student(school=self.school, student_id='X-1', first_name='Ada')
        enroll_student(student=student, term=self.term, stream=self.stream_a)

        self.teacher = create_user(
            is_active=True,
            first_name='Jane',
            last_name='Doe',
            phone_number='+233200000099',
            email='jane@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
        )
        ClassTeacher.objects.create(
            teacher=self.teacher,
            class_level=self.class_with_streams,
            stream=self.stream_a,
            term=self.term,
        )

        self.list_url = reverse('academics-classes')
        self.stats_url = reverse('academics-classes-stats')
        self.subjects_url = reverse('academics-classes-subjects')

    def test_class_list_returns_stream_rows(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data['term_id']), str(self.term.id))

        by_name = {item['name']: item for item in response.data['results']}
        self.assertEqual(set(by_name), {'Nursery 1 A', 'Nursery 1 B', 'Nursery 2'})

        nursery_a = by_name['Nursery 1 A']
        self.assertEqual(str(nursery_a['id']), str(self.stream_a.id))
        self.assertEqual(nursery_a['level_name'], 'Kindergarten')
        self.assertEqual(nursery_a['students_count'], 1)
        self.assertEqual(nursery_a['subjects_count'], 1)
        self.assertTrue(nursery_a['is_assigned'])
        self.assertTrue(nursery_a['needs_attention'])
        self.assertEqual(nursery_a['unassigned_subjects_count'], 1)
        self.assertEqual(nursery_a['class_teacher']['full_name'], 'Jane Doe')

        nursery_b = by_name['Nursery 1 B']
        self.assertEqual(nursery_b['students_count'], 0)
        self.assertFalse(nursery_b['is_assigned'])
        self.assertIsNone(nursery_b['class_teacher'])
        self.assertTrue(nursery_b['needs_attention'])

        nursery_2 = by_name['Nursery 2']
        self.assertEqual(str(nursery_2['id']), str(self.default_only_stream.id))
        self.assertTrue(nursery_2['is_default'])
        self.assertFalse(nursery_2['needs_attention'])
        self.assertEqual(nursery_2['subjects_count'], 0)

    def test_class_list_search_filters_results(self):
        response = self.client.get(self.list_url, {'search': 'Nursery 1 A'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [item['name'] for item in response.data['results']]
        self.assertEqual(names, ['Nursery 1 A'])

    def test_class_stats(self):
        response = self.client.get(self.stats_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data['term_id']), str(self.term.id))
        self.assertEqual(response.data['total_classes'], 3)
        self.assertEqual(response.data['total_students'], 1)
        self.assertEqual(response.data['total_teachers_assigned'], 1)
        self.assertEqual(response.data['unassigned_classes'], 2)
        # Literacy on Nursery 1 is unassigned for both stream A and B
        self.assertEqual(response.data['unassigned_class_subjects'], 2)
        self.assertEqual(response.data['empty_classes'], 2)
        self.assertEqual(response.data['classes_with_students'], 1)

    def test_subject_class_pairings(self):
        language = Subject.objects.create(
            school=self.school,
            name='Ghanaian Language',
            is_system_generated=False,
        )
        LevelSubject.objects.create(
            school=self.school,
            level=self.level,
            subject=language,
            is_system_generated=False,
        )
        language_class_subject = ClassSubject.objects.create(
            school=self.school,
            class_level=self.class_default_only,
            subject=language,
            is_system_generated=False,
        )
        group_twi = SubjectGroup.objects.create(
            class_subject=language_class_subject,
            name='Twi',
        )
        SubjectGroup.objects.create(
            class_subject=language_class_subject,
            name='Ga',
        )
        nursery_student = create_student(
            school=self.school,
            student_id='X-2',
            first_name='Kojo',
        )
        enroll_student(
            student=nursery_student,
            term=self.term,
            stream=self.default_only_stream,
        )
        StudentSubjectGroup.objects.create(
            student=nursery_student,
            class_subject=language_class_subject,
            subject_group=group_twi,
            academic_year=self.academic_year,
        )
        TeachingAssignment.objects.create(
            teacher=self.teacher,
            class_subject=language_class_subject,
            subject_group=group_twi,
            term=self.term,
        )

        response = self.client.get(self.subjects_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        by_key = {
            (item['subject_name'], item['group_name'], item['class_name']): item
            for item in response.data['results']
        }
        self.assertEqual(
            set(by_key),
            {
                ('Literacy', None, 'Nursery 1 A'),
                ('Literacy', None, 'Nursery 1 B'),
                ('Ghanaian Language', 'Ga', 'Nursery 2'),
                ('Ghanaian Language', 'Twi', 'Nursery 2'),
            },
        )

        literacy_a = by_key[('Literacy', None, 'Nursery 1 A')]
        self.assertEqual(literacy_a['students_count'], 1)
        self.assertIsNone(literacy_a['teacher'])
        self.assertTrue(literacy_a['needs_attention'])
        self.assertEqual(literacy_a['kind'], 'class_subject')

        literacy_b = by_key[('Literacy', None, 'Nursery 1 B')]
        self.assertEqual(literacy_b['students_count'], 0)
        self.assertTrue(literacy_b['needs_attention'])

        twi = by_key[('Ghanaian Language', 'Twi', 'Nursery 2')]
        self.assertEqual(twi['students_count'], 1)
        self.assertEqual(twi['teacher']['full_name'], 'Jane Doe')
        self.assertFalse(twi['needs_attention'])
        self.assertEqual(twi['kind'], 'subject_group')

        ga = by_key[('Ghanaian Language', 'Ga', 'Nursery 2')]
        self.assertEqual(ga['students_count'], 0)
        self.assertIsNone(ga['teacher'])
        self.assertTrue(ga['needs_attention'])

        search = self.client.get(self.subjects_url, {'search': 'Twi'})
        self.assertEqual(
            [item['group_name'] for item in search.data['results']],
            ['Twi'],
        )
