from datetime import date

from django.test import TestCase

from accounts.tests.factories import create_user, user_school
from assessments.services.report import _next_term_begins
from schools.models import AcademicYear, Term


class ReportNextTermBeginsTests(TestCase):
    def setUp(self):
        self.school = user_school(create_user(is_active=True))
        self.year = AcademicYear.objects.create(
            school=self.school,
            academic_year='2025/2026',
            start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31),
            is_active=True,
        )
        self.term1 = Term.objects.create(
            school=self.school,
            academic_year=self.year,
            term=Term.TermChoices.FIRST_TERM,
            start_date=date(2025, 9, 1),
            end_date=date(2025, 12, 15),
            is_active=True,
        )

    def test_same_day_start_still_shows_the_date(self):
        Term.objects.create(
            school=self.school,
            academic_year=self.year,
            term=Term.TermChoices.SECOND_TERM,
            start_date=date(2025, 12, 15),
            end_date=date(2026, 4, 1),
            is_active=False,
        )

        self.assertEqual(
            _next_term_begins(school=self.school, term=self.term1),
            '15th December, 2025',
        )

    def test_day_after_start_shows_the_date(self):
        Term.objects.create(
            school=self.school,
            academic_year=self.year,
            term=Term.TermChoices.SECOND_TERM,
            start_date=date(2025, 12, 16),
            end_date=date(2026, 4, 1),
            is_active=False,
        )

        self.assertEqual(
            _next_term_begins(school=self.school, term=self.term1),
            '16th December, 2025',
        )

    def test_blank_when_the_next_term_is_missing(self):
        self.assertIsNone(_next_term_begins(school=self.school, term=self.term1))

    def test_year_change_uses_the_next_year_first_term(self):
        term3 = Term.objects.create(
            school=self.school,
            academic_year=self.year,
            term=Term.TermChoices.THIRD_TERM,
            start_date=date(2026, 4, 15),
            end_date=date(2026, 7, 31),
            is_active=False,
        )
        next_year = AcademicYear.objects.create(
            school=self.school,
            academic_year='2026/2027',
            start_date=date(2026, 7, 31),
            end_date=date(2027, 7, 30),
            is_active=False,
        )
        Term.objects.create(
            school=self.school,
            academic_year=next_year,
            term=Term.TermChoices.FIRST_TERM,
            start_date=date(2026, 7, 31),
            end_date=date(2026, 12, 15),
            is_active=False,
        )

        self.assertEqual(
            _next_term_begins(school=self.school, term=term3),
            '31st July, 2026',
        )
