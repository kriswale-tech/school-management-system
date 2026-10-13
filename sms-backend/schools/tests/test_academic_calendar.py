from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, Level
from accounts.models import User
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from assessments.models import AssessmentConfig
from fees.models import FeeStructure
from schools.models import AcademicYear, SchoolSetup, Term
from schools.services.academic import save_academic_year_setup
from students.tests.factories import create_student, enroll_student, ensure_default_stream


def _schedule(label, first_start, first_end, second_start, second_end, third_start, third_end):
    return {
        'academic_year': label,
        'terms': [
            {'term': 'first_term', 'start_date': first_start.isoformat(), 'end_date': first_end.isoformat()},
            {'term': 'second_term', 'start_date': second_start.isoformat(), 'end_date': second_end.isoformat()},
            {'term': 'third_term', 'start_date': third_start.isoformat(), 'end_date': third_end.isoformat()},
        ],
    }


def _year_2025():
    return _schedule(
        '2025/2026',
        date(2025, 9, 1),
        date(2025, 12, 10),
        date(2026, 1, 6),
        date(2026, 4, 2),
        date(2026, 4, 20),
        date(2026, 7, 31),
    )


def _year_2026():
    return _schedule(
        '2026/2027',
        date(2026, 9, 1),
        date(2026, 12, 10),
        date(2027, 1, 6),
        date(2027, 4, 2),
        date(2027, 4, 20),
        date(2027, 7, 31),
    )


class AcademicCalendarAPITests(APITestCase):
    def setUp(self):
        self.admin = create_user(is_active=True, email='calendar-admin@test.com')
        set_client_auth_cookies(self.client, self.admin)
        self.school = user_school(self.admin)
        self.school.setup_completed = True
        self.school.save(update_fields=['setup_completed', 'updated_at'])
        self.list_url = reverse('school-academic-year-list')
        self._create_year(_year_2025(), active_term='third_term', is_active=True)

    def _create_year(self, payload, *, active_term, is_active):
        year = AcademicYear.objects.create(
            school=self.school,
            academic_year=payload['academic_year'],
            start_date=payload['terms'][0]['start_date'],
            end_date=payload['terms'][-1]['end_date'],
            is_active=is_active,
        )
        terms = {}
        for item in payload['terms']:
            terms[item['term']] = Term.objects.create(
                school=self.school,
                academic_year=year,
                term=item['term'],
                start_date=item['start_date'],
                end_date=item['end_date'],
                is_active=is_active and item['term'] == active_term,
            )
        return year, terms

    def test_list_marks_the_active_term_and_offers_the_next_year(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['years']), 1)
        year = response.data['years'][0]
        self.assertEqual(year['status'], 'current')
        active = next(term for term in year['terms'] if term['is_active'])
        self.assertEqual(active['term'], 'third_term')
        self.assertEqual(response.data['next_year_label'], '2026/2027')
        today = date.today().isoformat()
        for term in year['terms']:
            if term['end_date'] < today:
                self.assertFalse(term['can_edit_dates'])

    def test_create_next_year_stays_inactive_and_leaves_setup_alone(self):
        SchoolSetup.objects.create(
            school=self.school,
            current_step=SchoolSetup.SetupStep.COMPLETED,
            completed_steps=['school_profile', 'academic_year_term'],
            progress_percentage=100,
        )
        level = Level.objects.create(school=self.school, name='Primary', is_system_generated=False)
        current = Term.objects.get(school=self.school, is_active=True)
        AssessmentConfig.objects.create(
            level=level,
            term=current,
            continuous_assessment_weight=Decimal('30'),
            exam_weight=Decimal('70'),
            result_type=AssessmentConfig.ResultType.POSITION,
        )

        response = self.client.post(self.list_url, _year_2026(), format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertNotIn('next_step', response.data)
        created = AcademicYear.objects.get(school=self.school, academic_year='2026/2027')
        self.assertFalse(created.is_active)
        self.assertTrue(Term.objects.get(school=self.school, is_active=True).academic_year.academic_year == '2025/2026')
        setup = SchoolSetup.objects.get(school=self.school)
        self.assertEqual(setup.current_step, SchoolSetup.SetupStep.COMPLETED)
        self.assertEqual(
            AssessmentConfig.objects.filter(term__academic_year=created).count(),
            3,
        )

    def test_create_rejects_a_skipped_year(self):
        payload = _year_2026()
        payload['academic_year'] = '2027/2028'
        payload['terms'][0]['start_date'] = '2027-09-01'
        payload['terms'][0]['end_date'] = '2027-12-10'
        payload['terms'][1]['start_date'] = '2028-01-06'
        payload['terms'][1]['end_date'] = '2028-04-02'
        payload['terms'][2]['start_date'] = '2028-04-20'
        payload['terms'][2]['end_date'] = '2028-07-31'

        response = self.client.post(self.list_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(AcademicYear.objects.filter(academic_year='2027/2028').exists())

    def test_teacher_cannot_add_a_year(self):
        teacher = create_user(
            phone_number='+233200000041',
            email='calendar-teacher@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
            is_active=True,
        )
        set_client_auth_cookies(self.client, teacher, school=self.school)

        response = self.client.post(self.list_url, _year_2026(), format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_past_year_dates_stay_fixed(self):
        past, _terms = self._create_year(
            _schedule(
                '2024/2025',
                date(2024, 9, 1),
                date(2024, 12, 10),
                date(2025, 1, 6),
                date(2025, 4, 2),
                date(2025, 4, 20),
                date(2025, 7, 31),
            ),
            active_term='third_term',
            is_active=False,
        )

        response = self.client.patch(
            reverse('school-academic-year-detail', kwargs={'year_id': past.id}),
            _schedule(
                '2024/2025',
                date(2024, 9, 8),
                date(2024, 12, 10),
                date(2025, 1, 6),
                date(2025, 4, 2),
                date(2025, 4, 20),
                date(2025, 7, 31),
            ),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upcoming_year_dates_can_change(self):
        self.client.post(self.list_url, _year_2026(), format='json')
        year = AcademicYear.objects.get(school=self.school, academic_year='2026/2027')
        payload = _year_2026()
        payload['terms'][0]['end_date'] = '2026-12-18'
        payload['terms'][1]['start_date'] = '2027-01-11'

        response = self.client.patch(
            reverse('school-academic-year-detail', kwargs={'year_id': year.id}),
            payload,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        first = Term.objects.get(academic_year=year, term='first_term')
        self.assertEqual(first.end_date, date(2026, 12, 18))
        self.assertFalse(year.is_active)

    def test_switch_moves_only_the_active_term(self):
        self.client.post(self.list_url, _year_2026(), format='json')
        target = Term.objects.get(
            school=self.school,
            academic_year__academic_year='2026/2027',
            term='first_term',
        )
        preview = self.client.get(
            reverse('school-term-switch-preview', kwargs={'term_id': target.id}),
        )
        self.assertTrue(preview.data['can_switch'])
        self.assertTrue(preview.data['warnings'])

        response = self.client.post(
            reverse('school-term-activate', kwargs={'term_id': target.id}),
            {'acknowledge_warnings': True},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        target.refresh_from_db()
        self.assertTrue(target.is_active)
        self.assertTrue(target.academic_year.is_active)
        previous = Term.objects.get(school=self.school, academic_year__academic_year='2025/2026', term='third_term')
        self.assertFalse(previous.is_active)
        self.assertFalse(previous.academic_year.is_active)
        self.assertEqual(AcademicYear.objects.filter(school=self.school, is_active=True).count(), 1)
        self.assertEqual(Term.objects.filter(school=self.school, is_active=True).count(), 1)

    def test_switch_refuses_to_skip_a_term(self):
        year = AcademicYear.objects.get(school=self.school)
        year.is_active = True
        year.save(update_fields=['is_active', 'updated_at'])
        Term.objects.filter(school=self.school).update(is_active=False)
        first = Term.objects.get(school=self.school, term='first_term')
        first.is_active = True
        first.save(update_fields=['is_active', 'updated_at'])
        third = Term.objects.get(school=self.school, term='third_term')

        response = self.client.post(
            reverse('school-term-activate', kwargs={'term_id': third.id}),
            {'acknowledge_warnings': True},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        third.refresh_from_db()
        self.assertFalse(third.is_active)

    def test_switch_requires_warning_acknowledgement(self):
        self.client.post(self.list_url, _year_2026(), format='json')
        target = Term.objects.get(
            school=self.school,
            academic_year__academic_year='2026/2027',
            term='first_term',
        )

        response = self.client.post(
            reverse('school-term-activate', kwargs={'term_id': target.id}),
            {'acknowledge_warnings': False},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        target.refresh_from_db()
        self.assertFalse(target.is_active)

    def test_switch_warns_about_unreleased_reports(self):
        student = create_student(school=self.school, student_id='CAL-0001')
        level = Level.objects.create(school=self.school, name='JHS', is_system_generated=False)
        class_level = ClassLevel.objects.create(
            school=self.school,
            level=level,
            name='JHS 1',
            is_system_generated=False,
        )
        stream = ensure_default_stream(class_level)
        current = Term.objects.get(school=self.school, is_active=True)
        enroll_student(student=student, term=current, stream=stream)
        self.client.post(self.list_url, _year_2026(), format='json')
        target = Term.objects.get(
            school=self.school,
            academic_year__academic_year='2026/2027',
            term='first_term',
        )
        FeeStructure.objects.create(school=self.school, term=target, created_by=self.admin, status=FeeStructure.Status.APPLIED)

        preview = self.client.get(reverse('school-term-switch-preview', kwargs={'term_id': target.id}))

        self.assertTrue(preview.data['can_switch'])
        self.assertTrue(any('unreleased' in warning for warning in preview.data['warnings']))

    def test_ended_term_on_the_current_year_stays_fixed(self):
        from datetime import timedelta

        today = date.today()
        AcademicYear.objects.filter(school=self.school).delete()
        first_end = today - timedelta(days=10)
        first_start = first_end - timedelta(days=90)
        label = f'{first_start.year}/{first_start.year + 1}'
        second_start = first_end
        second_end = date(first_start.year + 1, 3, 15)
        third_start = date(first_start.year + 1, 4, 6)
        third_end = date(first_start.year + 1, 7, 31)
        year, terms = self._create_year(
            _schedule(label, first_start, first_end, second_start, second_end, third_start, third_end),
            active_term='second_term',
            is_active=True,
        )
        payload = _schedule(
            label,
            first_start,
            first_end + timedelta(days=3),
            second_start,
            second_end,
            third_start,
            third_end,
        )

        response = self.client.patch(
            reverse('school-academic-year-detail', kwargs={'year_id': year.id}),
            payload,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        terms['first_term'].refresh_from_db()
        self.assertEqual(terms['first_term'].end_date, first_end)

    def test_setup_save_still_activates_the_year(self):
        result = save_academic_year_setup(
            self.school,
            {
                'academic_year': '2026/2027',
                'current_term': 'first_term',
                'terms': [
                    {'term': 'first_term', 'start_date': date(2026, 9, 1), 'end_date': date(2026, 12, 15)},
                    {'term': 'second_term', 'start_date': date(2027, 1, 6), 'end_date': date(2027, 4, 1)},
                    {'term': 'third_term', 'start_date': date(2027, 4, 8), 'end_date': date(2027, 7, 31)},
                ],
            },
        )

        self.assertEqual(result['academic_year'], '2026/2027')
        self.assertTrue(result['is_active'])
        self.assertEqual(result['current_term'], 'first_term')
        self.assertEqual(AcademicYear.objects.filter(school=self.school, is_active=True).count(), 1)
