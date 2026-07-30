from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from schools.models import AcademicYear, SchoolSetup, Term
from schools.tests.factories import academic_year_term_payload, create_school_setup


class SchoolsAPITestCase(APITestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        set_client_auth_cookies(self.client, self.user)
        self.school = user_school(self.user)


class SetupAcademicYearTermViewTests(SchoolsAPITestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('school-setup-academic-year-term')

    def test_get_returns_empty_setup_when_none_exists(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['academic_year'])
        self.assertEqual(response.data['terms'], [])

    def test_post_blocked_without_school_profile_step(self):
        create_school_setup(self.school)

        response = self.client.post(
            self.url,
            academic_year_term_payload(),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data['raw_detail'])

    def test_post_creates_active_year_and_single_active_term(self):
        create_school_setup(
            self.school,
            completed_steps=[SchoolSetup.SetupStep.SCHOOL_PROFILE],
            current_step=SchoolSetup.SetupStep.ACADEMIC_YEAR_TERM,
        )

        response = self.client.post(
            self.url,
            academic_year_term_payload(),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['academic_year'], '2026/2027')
        self.assertEqual(response.data['current_term'], 'first_term')
        self.assertEqual(response.data['next_step'], 'classes_and_subjects')
        self.assertIn('academic_year_term', response.data['completed_steps'])

        self.assertEqual(AcademicYear.objects.filter(school=self.school, is_active=True).count(), 1)
        self.assertEqual(Term.objects.filter(school=self.school, is_active=True).count(), 1)

        active_term = Term.objects.get(school=self.school, is_active=True)
        active_year = AcademicYear.objects.get(school=self.school, is_active=True)
        self.assertEqual(active_term.academic_year_id, active_year.id)
        self.assertEqual(active_term.term, Term.TermChoices.FIRST_TERM)

    def test_get_returns_saved_setup(self):
        create_school_setup(
            self.school,
            completed_steps=[SchoolSetup.SetupStep.SCHOOL_PROFILE],
            current_step=SchoolSetup.SetupStep.ACADEMIC_YEAR_TERM,
        )
        self.client.post(self.url, academic_year_term_payload(), format='json')

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['academic_year'], '2026/2027')
        self.assertEqual(len(response.data['terms']), 3)

    def test_switching_active_year_deactivates_old_terms(self):
        create_school_setup(
            self.school,
            completed_steps=[SchoolSetup.SetupStep.SCHOOL_PROFILE],
            current_step=SchoolSetup.SetupStep.ACADEMIC_YEAR_TERM,
        )
        self.client.post(self.url, academic_year_term_payload(), format='json')

        new_payload = academic_year_term_payload(
            academic_year='2027/2028',
            current_term='second_term',
            terms=[
                {
                    'term': 'first_term',
                    'start_date': '2027-09-01',
                    'end_date': '2027-12-15',
                },
                {
                    'term': 'second_term',
                    'start_date': '2027-12-15',
                    'end_date': '2028-04-01',
                },
                {
                    'term': 'third_term',
                    'start_date': '2028-04-01',
                    'end_date': '2028-07-31',
                },
            ],
        )
        response = self.client.post(self.url, new_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AcademicYear.objects.filter(school=self.school, is_active=True).count(), 1)
        self.assertEqual(Term.objects.filter(school=self.school, is_active=True).count(), 1)

        active_year = AcademicYear.objects.get(school=self.school, is_active=True)
        self.assertEqual(active_year.academic_year, '2027/2028')

        inactive_year = AcademicYear.objects.get(school=self.school, academic_year='2026/2027')
        self.assertFalse(inactive_year.is_active)
        self.assertFalse(inactive_year.terms.filter(is_active=True).exists())
