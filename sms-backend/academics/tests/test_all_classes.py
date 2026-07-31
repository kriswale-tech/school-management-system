from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, ClassStream, Level
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from schools.models import AcademicYear, Term
from students.tests.factories import create_student, enroll_student, ensure_default_stream


class AllClassesViewTests(APITestCase):
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
            name='Nursery',
            is_system_generated=False,
        )
        self.class_with_streams = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='Nursery 1',
            is_system_generated=False,
        )
        ensure_default_stream(self.class_with_streams)
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

        student = create_student(school=self.school, student_id='X-1', first_name='A')
        enroll_student(student=student, term=self.term, stream=self.stream_b)

        self.url = reverse('academics-levels-all-classes')

    def test_all_classes_flattens_streams_as_entries(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data['term_id']), str(self.term.id))
        level = response.data['levels'][0]
        self.assertEqual(level['name'], 'Nursery')

        by_name = {entry['display_name']: entry for entry in level['classes']}
        self.assertEqual(set(by_name), {'Nursery 1 B', 'Nursery 2'})

        named = by_name['Nursery 1 B']
        self.assertEqual(str(named['id']), str(self.stream_b.id))
        self.assertEqual(named['student_count'], 1)
        self.assertFalse(named['is_default'])

        default_only = by_name['Nursery 2']
        self.assertEqual(str(default_only['id']), str(self.default_only_stream.id))
        self.assertEqual(default_only['student_count'], 0)
        self.assertTrue(default_only['is_default'])
