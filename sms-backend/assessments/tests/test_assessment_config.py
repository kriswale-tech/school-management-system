from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from academics.models import Level
from accounts.tests.factories import create_school
from assessments.constants.grade_templates import (
    BECE_STANDARD_NUMERICAL_GRADES,
    GES_INTERNAL_LETTER_GRADES,
)
from assessments.models import AssessmentConfig
from assessments.services import (
    apply_grade_template,
    clear_grade_configuration,
    replace_grade_bands,
    validate_assessment_config_ready,
    validate_grade_bands,
)


class AssessmentConfigModelTests(TestCase):
    def setUp(self):
        self.school = create_school()
        self.level = Level.objects.create(
            school=self.school,
            name='Junior High',
            is_system_generated=False,
        )

    def test_creates_with_default_weights_summing_to_100(self):
        config = AssessmentConfig.objects.create(
            level=self.level,
            result_type=AssessmentConfig.ResultType.POSITION,
        )

        self.assertEqual(config.continuous_assessment_weight, Decimal('40.00'))
        self.assertEqual(config.exam_weight, Decimal('60.00'))
        self.assertIsNone(config.grade_type)

    def test_rejects_weights_that_do_not_sum_to_100(self):
        with self.assertRaises(ValidationError) as ctx:
            AssessmentConfig.objects.create(
                level=self.level,
                continuous_assessment_weight=Decimal('30.00'),
                exam_weight=Decimal('60.00'),
                result_type=AssessmentConfig.ResultType.POSITION,
            )

        self.assertIn('continuous_assessment_weight', ctx.exception.message_dict)

    def test_requires_grade_type_when_result_includes_grades(self):
        with self.assertRaises(ValidationError) as ctx:
            AssessmentConfig.objects.create(
                level=self.level,
                result_type=AssessmentConfig.ResultType.GRADE,
            )

        self.assertIn('grade_type', ctx.exception.message_dict)

    def test_rejects_grade_type_for_position_only(self):
        with self.assertRaises(ValidationError) as ctx:
            AssessmentConfig.objects.create(
                level=self.level,
                result_type=AssessmentConfig.ResultType.POSITION,
                grade_type=AssessmentConfig.GradeType.LETTER,
            )

        self.assertIn('grade_type', ctx.exception.message_dict)

    def test_one_config_per_level(self):
        AssessmentConfig.objects.create(
            level=self.level,
            result_type=AssessmentConfig.ResultType.POSITION,
        )

        with self.assertRaises(ValidationError) as ctx:
            AssessmentConfig.objects.create(
                level=self.level,
                result_type=AssessmentConfig.ResultType.POSITION,
            )

        self.assertIn('level', ctx.exception.message_dict)


class GradeBandValidationTests(TestCase):
    def test_letter_template_is_valid(self):
        validate_grade_bands(GES_INTERNAL_LETTER_GRADES)

    def test_numerical_template_is_valid(self):
        validate_grade_bands(BECE_STANDARD_NUMERICAL_GRADES)

    def test_rejects_overlap(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_grade_bands([
                {'grade': 'A', 'min_score': 80, 'max_score': 100, 'remark': 'Excellent'},
                {'grade': 'B', 'min_score': 70, 'max_score': 85, 'remark': 'Good'},
                {'grade': 'F', 'min_score': 0, 'max_score': 69, 'remark': 'Fail'},
            ])

        self.assertTrue(
            any('overlap' in str(error).lower() for error in ctx.exception.messages),
        )

    def test_rejects_gap(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_grade_bands([
                {'grade': 'A', 'min_score': 80, 'max_score': 100, 'remark': 'Excellent'},
                {'grade': 'B', 'min_score': 70, 'max_score': 78, 'remark': 'Good'},
                {'grade': 'F', 'min_score': 0, 'max_score': 69, 'remark': 'Fail'},
            ])

        self.assertTrue(
            any('gap' in str(error).lower() for error in ctx.exception.messages),
        )

    def test_rejects_incomplete_coverage(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_grade_bands([
                {'grade': 'A', 'min_score': 50, 'max_score': 100, 'remark': 'Pass'},
            ])

        self.assertTrue(
            any('start at 0' in str(error) for error in ctx.exception.messages),
        )


class AssessmentConfigServiceTests(TestCase):
    def setUp(self):
        self.school = create_school()
        self.level = Level.objects.create(
            school=self.school,
            name='Junior High',
            is_system_generated=False,
        )
        self.config = AssessmentConfig.objects.create(
            level=self.level,
            result_type=AssessmentConfig.ResultType.GRADE_AND_POSITION,
            grade_type=AssessmentConfig.GradeType.LETTER,
        )

    def test_apply_letter_template(self):
        bands = apply_grade_template(
            self.config,
            AssessmentConfig.GradeType.LETTER,
        )

        self.assertEqual(len(bands), len(GES_INTERNAL_LETTER_GRADES))
        self.assertEqual(
            {(band.grade, band.min_score, band.max_score, band.remark) for band in bands},
            {
                (item['grade'], item['min_score'], item['max_score'], item['remark'])
                for item in GES_INTERNAL_LETTER_GRADES
            },
        )
        validate_assessment_config_ready(self.config)

    def test_apply_numerical_template_replaces_bands(self):
        apply_grade_template(self.config, AssessmentConfig.GradeType.LETTER)
        bands = apply_grade_template(
            self.config,
            AssessmentConfig.GradeType.NUMERICAL,
        )

        self.config.refresh_from_db()
        self.assertEqual(self.config.grade_type, AssessmentConfig.GradeType.NUMERICAL)
        self.assertEqual(len(bands), len(BECE_STANDARD_NUMERICAL_GRADES))
        self.assertEqual(self.config.grade_bands.count(), 9)

    def test_replace_grade_bands_with_custom_ranges(self):
        apply_grade_template(self.config, AssessmentConfig.GradeType.LETTER)
        custom = [
            {'grade': 'A', 'min_score': 75, 'max_score': 100, 'remark': 'Excellent'},
            {'grade': 'B', 'min_score': 50, 'max_score': 74, 'remark': 'Good'},
            {'grade': 'F', 'min_score': 0, 'max_score': 49, 'remark': 'Fail'},
        ]

        bands = replace_grade_bands(self.config, custom)

        self.assertEqual(len(bands), 3)
        self.assertEqual(self.config.grade_bands.get(grade='A').min_score, 75)
        validate_assessment_config_ready(self.config)

    def test_clear_grade_configuration_switches_to_position(self):
        apply_grade_template(self.config, AssessmentConfig.GradeType.LETTER)

        clear_grade_configuration(self.config)
        self.config.refresh_from_db()

        self.assertEqual(
            self.config.result_type,
            AssessmentConfig.ResultType.POSITION,
        )
        self.assertIsNone(self.config.grade_type)
        self.assertEqual(self.config.grade_bands.count(), 0)

    def test_ready_validation_requires_bands_for_grade_results(self):
        with self.assertRaises(ValidationError):
            validate_assessment_config_ready(self.config)
