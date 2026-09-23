from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import Level
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from assessments.models import AssessmentConfig
from assessments.services import apply_grade_template
from assessments.services.scoring import compute_class_score, compute_exam_contribution, compute_total
from assessments.services.term_config import (
    copy_forward_assessment_configs,
    copy_forward_to_sibling_terms,
    get_term_assessment_config,
)
from schools.models import AcademicYear, SchoolSetup, Term
from schools.tests.factories import create_school_setup
from assessments.constants.grade_templates import GES_INTERNAL_LETTER_GRADES


class TermAssessmentConfigTests(TestCase):
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
        self.term2 = Term.objects.create(
            school=self.school,
            academic_year=self.year,
            term=Term.TermChoices.SECOND_TERM,
            start_date=date(2026, 1, 7),
            end_date=date(2026, 4, 1),
            is_active=False,
        )
        self.level = Level.objects.create(
            school=self.school,
            name='Primary',
            is_system_generated=False,
        )
        self.config_term1 = AssessmentConfig.objects.create(
            level=self.level,
            term=self.term1,
            continuous_assessment_weight=Decimal('40'),
            exam_weight=Decimal('60'),
            result_type=AssessmentConfig.ResultType.POSITION,
        )

    def test_copy_forward_clones_weights_and_leaves_source(self):
        created = copy_forward_assessment_configs(
            school=self.school,
            target_term=self.term2,
            source_term=self.term1,
        )
        self.assertEqual(len(created), 1)
        clone = created[0]
        self.assertEqual(clone.term_id, self.term2.id)
        self.assertEqual(clone.continuous_assessment_weight, Decimal('40.00'))
        self.config_term1.refresh_from_db()
        self.assertEqual(self.config_term1.continuous_assessment_weight, Decimal('40.00'))

        clone.continuous_assessment_weight = Decimal('50')
        clone.exam_weight = Decimal('50')
        clone.save()

        self.config_term1.refresh_from_db()
        self.assertEqual(self.config_term1.continuous_assessment_weight, Decimal('40.00'))
        self.assertEqual(
            get_term_assessment_config(level_id=self.level.id, term_id=self.term1.id)
            .continuous_assessment_weight,
            Decimal('40.00'),
        )
        self.assertEqual(
            get_term_assessment_config(level_id=self.level.id, term_id=self.term2.id)
            .continuous_assessment_weight,
            Decimal('50.00'),
        )

    def test_same_marks_yield_different_totals_across_terms(self):
        AssessmentConfig.objects.create(
            level=self.level,
            term=self.term2,
            continuous_assessment_weight=Decimal('50'),
            exam_weight=Decimal('50'),
            result_type=AssessmentConfig.ResultType.POSITION,
        )
        items = [type('Item', (), {'id': '1', 'max_marks': Decimal('20')})()]
        marks = {'1': Decimal('16')}
        class_score_t1 = compute_class_score(marks, items, Decimal('40'))
        class_score_t2 = compute_class_score(marks, items, Decimal('50'))
        exam_t1 = compute_exam_contribution(Decimal('70'), Decimal('60'))
        exam_t2 = compute_exam_contribution(Decimal('70'), Decimal('50'))
        self.assertEqual(compute_total(class_score_t1, exam_t1), Decimal('74.00'))
        self.assertEqual(compute_total(class_score_t2, exam_t2), Decimal('75.00'))

    def test_copy_forward_to_siblings_does_not_overwrite(self):
        existing = AssessmentConfig.objects.create(
            level=self.level,
            term=self.term2,
            continuous_assessment_weight=Decimal('30'),
            exam_weight=Decimal('70'),
            result_type=AssessmentConfig.ResultType.POSITION,
        )
        copy_forward_to_sibling_terms(school=self.school, source_term=self.term1)
        existing.refresh_from_db()
        self.assertEqual(existing.continuous_assessment_weight, Decimal('30.00'))

    def test_copy_forward_clones_grade_bands(self):
        self.config_term1.result_type = AssessmentConfig.ResultType.GRADE_AND_POSITION
        self.config_term1.grade_type = AssessmentConfig.GradeType.LETTER
        self.config_term1.save()
        apply_grade_template(self.config_term1, AssessmentConfig.GradeType.LETTER)
        copy_forward_assessment_configs(
            school=self.school,
            target_term=self.term2,
            source_term=self.term1,
        )
        clone = AssessmentConfig.objects.get(level=self.level, term=self.term2)
        self.assertEqual(clone.grade_bands.count(), len(GES_INTERNAL_LETTER_GRADES))
        clone.grade_bands.filter(grade='A').update(min_score=90)
        self.assertEqual(self.config_term1.grade_bands.get(grade='A').min_score, 80)


class AssessmentSettingsApiTests(APITestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        set_client_auth_cookies(self.client, self.user)
        self.school = user_school(self.user)
        create_school_setup(
            self.school,
            completed_steps=[
                SchoolSetup.SetupStep.SCHOOL_PROFILE,
                SchoolSetup.SetupStep.ACADEMIC_YEAR_TERM,
                SchoolSetup.SetupStep.CLASSES_AND_SUBJECTS,
            ],
            current_step=SchoolSetup.SetupStep.ASSESSMENT,
        )
        today = date.today()
        self.year = AcademicYear.objects.create(
            school=self.school,
            academic_year='2024/2025',
            start_date=today - timedelta(days=400),
            end_date=today + timedelta(days=10),
            is_active=True,
        )
        self.past_term = Term.objects.create(
            school=self.school,
            academic_year=self.year,
            term=Term.TermChoices.FIRST_TERM,
            start_date=today - timedelta(days=200),
            end_date=today - timedelta(days=30),
            is_active=False,
        )
        self.current_term = Term.objects.create(
            school=self.school,
            academic_year=self.year,
            term=Term.TermChoices.SECOND_TERM,
            start_date=today - timedelta(days=20),
            end_date=today + timedelta(days=40),
            is_active=True,
        )
        self.level = Level.objects.create(
            school=self.school,
            name='JHS',
            is_system_generated=False,
        )
        AssessmentConfig.objects.create(
            level=self.level,
            term=self.current_term,
            continuous_assessment_weight=Decimal('40'),
            exam_weight=Decimal('60'),
            result_type=AssessmentConfig.ResultType.POSITION,
        )
        AssessmentConfig.objects.create(
            level=self.level,
            term=self.past_term,
            continuous_assessment_weight=Decimal('40'),
            exam_weight=Decimal('60'),
            result_type=AssessmentConfig.ResultType.POSITION,
        )
        self.settings_url = reverse('academics-assessments-settings')
        self.level_url = reverse(
            'academics-assessments-settings-level',
            kwargs={'level_id': self.level.id},
        )

    def test_get_returns_current_term_structure(self):
        response = self.client.get(self.settings_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data['term_id']), str(self.current_term.id))
        self.assertTrue(response.data['is_editable'])
        self.assertFalse(response.data['term_ended'])
        self.assertEqual(
            str(response.data['levels'][0]['config']['exam_weight']),
            '60.00',
        )

    def test_save_current_term_does_not_change_past_term(self):
        response = self.client.put(
            f'{self.level_url}?term_id={self.current_term.id}',
            {
                'continuous_assessment_weight': '50.00',
                'exam_weight': '50.00',
                'result_type': AssessmentConfig.ResultType.POSITION,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            AssessmentConfig.objects.get(level=self.level, term=self.current_term)
            .exam_weight,
            Decimal('50.00'),
        )
        self.assertEqual(
            AssessmentConfig.objects.get(level=self.level, term=self.past_term)
            .exam_weight,
            Decimal('60.00'),
        )

    def test_past_term_is_read_only(self):
        response = self.client.get(f'{self.settings_url}?term_id={self.past_term.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['term_ended'])
        self.assertFalse(response.data['is_editable'])

        blocked = self.client.put(
            f'{self.level_url}?term_id={self.past_term.id}',
            {
                'continuous_assessment_weight': '50.00',
                'exam_weight': '50.00',
                'result_type': AssessmentConfig.ResultType.POSITION,
            },
            format='json',
        )
        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            AssessmentConfig.objects.get(level=self.level, term=self.past_term)
            .exam_weight,
            Decimal('60.00'),
        )
