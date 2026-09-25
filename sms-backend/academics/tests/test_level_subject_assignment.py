from datetime import date
from uuid import uuid4

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
from students.tests.factories import ensure_default_stream
from teachers.models import TeachingAssignment


class LevelSubjectAssignmentTests(APITestCase):
    """Assign one teacher to a subject across every class in a level.

    Listed streams follow the classes page: named streams hide the default
    stream. Grouped subjects stay class-by-class.
    """

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
        self.primary_one = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='Primary 1',
            is_system_generated=False,
        )
        self.primary_one_default = ensure_default_stream(self.primary_one)
        self.primary_one_a = ClassStream.objects.create(
            class_level=self.primary_one,
            name='A',
            is_default=False,
        )
        self.primary_one_b = ClassStream.objects.create(
            class_level=self.primary_one,
            name='B',
            is_default=False,
        )
        self.primary_two = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='Primary 2',
            is_system_generated=False,
            order=2,
        )
        self.primary_two_stream = ensure_default_stream(self.primary_two)

        self.math = Subject.objects.create(
            school=self.school,
            name='Mathematics',
            is_system_generated=False,
        )
        self.english = Subject.objects.create(
            school=self.school,
            name='English',
            is_system_generated=False,
        )
        self.language = Subject.objects.create(
            school=self.school,
            name='Ghanaian Language',
            is_system_generated=False,
        )
        for subject in (self.math, self.english, self.language):
            LevelSubject.objects.create(
                school=self.school,
                level=self.level,
                subject=subject,
                is_system_generated=False,
            )

        self.math_p1 = ClassSubject.objects.create(
            school=self.school,
            class_level=self.primary_one,
            subject=self.math,
            is_system_generated=False,
        )
        self.math_p2 = ClassSubject.objects.create(
            school=self.school,
            class_level=self.primary_two,
            subject=self.math,
            is_system_generated=False,
        )
        self.english_p1 = ClassSubject.objects.create(
            school=self.school,
            class_level=self.primary_one,
            subject=self.english,
            is_system_generated=False,
        )
        self.language_p1 = ClassSubject.objects.create(
            school=self.school,
            class_level=self.primary_one,
            subject=self.language,
            is_system_generated=False,
        )
        SubjectGroup.objects.create(class_subject=self.language_p1, name='Twi')
        SubjectGroup.objects.create(class_subject=self.language_p1, name='Ga')

        self.teacher = create_user(
            is_active=True,
            first_name='Jane',
            last_name='Doe',
            phone_number='+233200000099',
            email='jane@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
        )
        self.other_teacher = create_user(
            is_active=True,
            first_name='Ama',
            last_name='Owusu',
            phone_number='+233200000098',
            email='ama@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
        )

        self.subjects_url = reverse(
            'academics-level-assignable-subjects',
            args=[self.level.id],
        )
        self.assign_url = reverse(
            'academics-level-subject-teacher-assign',
            args=[self.level.id],
        )
        self.teachers_url = reverse('academics-classes-teachers')

    def _assign(self, subject):
        return self.client.put(
            self.assign_url,
            {
                'teacher_id': str(self.teacher.id),
                'subject_id': str(subject.id),
            },
            format='json',
        )

    def _jane_summary(self, search=None):
        params = {'search': search} if search else None
        response = self.client.get(self.teachers_url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return next(
            (
                item['teaching_summary']
                for item in response.data['results']
                if item['full_name'] == 'Jane Doe'
            ),
            None,
        )

    def test_list_omits_grouped_subjects_and_counts_listed_streams(self):
        TeachingAssignment.objects.create(
            teacher=self.other_teacher,
            class_subject=self.math_p1,
            stream=self.primary_one_a,
            term=self.term,
        )

        response = self.client.get(self.subjects_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['level_name'], 'Lower Primary')
        by_name = {item['name']: item for item in response.data['results']}
        self.assertEqual(set(by_name), {'Mathematics', 'English'})
        self.assertEqual(by_name['Mathematics']['classes_count'], 3)
        self.assertEqual(by_name['Mathematics']['assigned_classes_count'], 1)
        self.assertEqual(by_name['English']['classes_count'], 2)
        self.assertEqual(by_name['English']['assigned_classes_count'], 0)

    def test_assign_creates_one_row_per_listed_stream_and_replaces(self):
        TeachingAssignment.objects.create(
            teacher=self.other_teacher,
            class_subject=self.math_p1,
            stream=self.primary_one_a,
            term=self.term,
        )

        response = self._assign(self.math)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['assigned_count'], 3)
        self.assertEqual(response.data['replaced_count'], 1)
        self.assertEqual(response.data['skipped_grouped_classes'], [])
        self.assertEqual(response.data['subject_name'], 'Mathematics')

        assignments = TeachingAssignment.objects.filter(
            term=self.term,
            class_subject__subject=self.math,
        )
        self.assertEqual(assignments.count(), 3)
        self.assertEqual(
            set(assignments.values_list('stream_id', flat=True)),
            {
                self.primary_one_a.id,
                self.primary_one_b.id,
                self.primary_two_stream.id,
            },
        )
        self.assertFalse(
            assignments.filter(stream=self.primary_one_default).exists(),
        )
        self.assertFalse(assignments.exclude(teacher=self.teacher).exists())

    def test_assign_skips_classes_that_do_not_offer_the_subject(self):
        response = self._assign(self.english)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['assigned_count'], 2)
        self.assertFalse(
            TeachingAssignment.objects.filter(
                class_subject__class_level=self.primary_two,
                term=self.term,
            ).exists(),
        )

    def test_assign_skips_classes_where_the_subject_is_grouped(self):
        SubjectGroup.objects.create(class_subject=self.math_p2, name='Set 1')

        response = self._assign(self.math)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['assigned_count'], 2)
        self.assertEqual(response.data['skipped_grouped_classes'], ['Primary 2'])
        self.assertFalse(
            TeachingAssignment.objects.filter(
                class_subject=self.math_p2,
                term=self.term,
            ).exists(),
        )

    def test_whole_class_row_counts_as_replaced_for_every_stream(self):
        TeachingAssignment.objects.create(
            teacher=self.other_teacher,
            class_subject=self.math_p1,
            stream=None,
            term=self.term,
        )

        response = self._assign(self.math)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['replaced_count'], 2)
        self.assertFalse(
            TeachingAssignment.objects.filter(
                class_subject=self.math_p1,
                stream__isnull=True,
                term=self.term,
            ).exists(),
        )

    def test_grouped_subject_is_rejected(self):
        response = self._assign(self.language)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('subject_id', response.data['raw_detail'])
        self.assertFalse(
            TeachingAssignment.objects.filter(term=self.term).exists(),
        )

    def test_unknown_subject_is_rejected(self):
        response = self.client.put(
            self.assign_url,
            {
                'teacher_id': str(self.teacher.id),
                'subject_id': str(uuid4()),
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_level_is_not_found(self):
        url = reverse('academics-level-assignable-subjects', args=[uuid4()])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_summary_collapses_when_every_class_in_the_level_is_covered(self):
        response = self._assign(self.math)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self._jane_summary(),
            'teaches Mathematics in Lower Primary',
        )

    def test_summary_stays_expanded_when_a_class_is_missing(self):
        TeachingAssignment.objects.create(
            teacher=self.teacher,
            class_subject=self.math_p1,
            stream=self.primary_one_a,
            term=self.term,
        )
        TeachingAssignment.objects.create(
            teacher=self.teacher,
            class_subject=self.math_p1,
            stream=self.primary_one_b,
            term=self.term,
        )

        self.assertEqual(
            self._jane_summary(),
            'teaches Mathematics in Primary 1 A and Primary 1 B',
        )

    def test_whole_class_row_counts_toward_level_coverage(self):
        TeachingAssignment.objects.create(
            teacher=self.teacher,
            class_subject=self.math_p1,
            stream=None,
            term=self.term,
        )
        TeachingAssignment.objects.create(
            teacher=self.teacher,
            class_subject=self.math_p2,
            stream=self.primary_two_stream,
            term=self.term,
        )

        self.assertEqual(
            self._jane_summary(),
            'teaches Mathematics in Lower Primary',
        )

    def test_search_still_matches_a_class_name_after_collapse(self):
        self._assign(self.math)

        self.assertEqual(
            self._jane_summary(search='Primary 1 A'),
            'teaches Mathematics in Lower Primary',
        )
        self.assertIsNone(self._jane_summary(search='does-not-match'))

    def test_grouped_assignments_are_not_collapsed_to_the_level(self):
        group = self.language_p1.groups.get(name='Twi')
        TeachingAssignment.objects.create(
            teacher=self.teacher,
            class_subject=self.language_p1,
            subject_group=group,
            term=self.term,
        )

        self.assertEqual(
            self._jane_summary(),
            'teaches Ghanaian Language in Primary 1 (Twi)',
        )
