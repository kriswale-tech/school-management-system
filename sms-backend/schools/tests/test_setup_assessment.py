from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import Level
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from assessments.constants.grade_templates import (
    BECE_STANDARD_NUMERICAL_GRADES,
    GES_INTERNAL_LETTER_GRADES,
)
from assessments.models import AssessmentConfig
from assessments.services import apply_grade_template
from schools.models import SchoolSetup
from schools.tests.factories import create_school_setup


class SetupAssessmentViewTests(APITestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        set_client_auth_cookies(self.client, self.user)
        self.school = user_school(self.user)
        self.url = reverse('school-setup-assessment')

    def test_get_returns_templates_and_empty_levels_when_none_exist(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['grade_templates']['letter'],
            GES_INTERNAL_LETTER_GRADES,
        )
        self.assertEqual(
            response.data['grade_templates']['numerical'],
            BECE_STANDARD_NUMERICAL_GRADES,
        )
        self.assertEqual(response.data['levels'], [])

    def test_get_returns_active_levels_with_null_config(self):
        Level.objects.create(
            school=self.school,
            name='Junior High',
            order=2,
            is_system_generated=False,
        )
        Level.objects.create(
            school=self.school,
            name='Primary',
            order=1,
            is_system_generated=False,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [level['level_name'] for level in response.data['levels']],
            ['Primary', 'Junior High'],
        )
        self.assertTrue(all(level['config'] is None for level in response.data['levels']))

    def test_get_includes_config_and_omits_inactive_levels(self):
        active_level = Level.objects.create(
            school=self.school,
            name='Junior High',
            order=1,
            is_system_generated=False,
        )
        inactive_level = Level.objects.create(
            school=self.school,
            name='Primary',
            order=2,
            is_active=False,
            is_system_generated=False,
        )
        config = AssessmentConfig.objects.create(
            level=active_level,
            result_type=AssessmentConfig.ResultType.GRADE_AND_POSITION,
            grade_type=AssessmentConfig.GradeType.LETTER,
        )
        apply_grade_template(config, AssessmentConfig.GradeType.LETTER)
        AssessmentConfig.objects.create(
            level=inactive_level,
            result_type=AssessmentConfig.ResultType.POSITION,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['levels']), 1)
        level_payload = response.data['levels'][0]
        self.assertEqual(level_payload['level_id'], str(active_level.id))
        self.assertEqual(
            level_payload['config']['result_type'],
            AssessmentConfig.ResultType.GRADE_AND_POSITION,
        )
        self.assertEqual(level_payload['config']['grade_type'], 'letter')
        self.assertEqual(
            len(level_payload['config']['grade_bands']),
            len(GES_INTERNAL_LETTER_GRADES),
        )
        self.assertEqual(level_payload['config']['grade_bands'][0]['grade'], 'A')


class SetupAssessmentMutationTests(APITestCase):
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
        self.level = Level.objects.create(
            school=self.school,
            name='Junior High',
            order=1,
            is_system_generated=False,
        )
        self.url = reverse(
            'school-setup-assessment-level-config',
            kwargs={'level_id': self.level.id},
        )
        self.complete_url = reverse('school-setup-assessment-complete')

    def _letter_payload(self, **overrides):
        data = {
            'continuous_assessment_weight': '40.00',
            'exam_weight': '60.00',
            'result_type': AssessmentConfig.ResultType.GRADE_AND_POSITION,
            'grade_type': AssessmentConfig.GradeType.LETTER,
            'grade_bands': GES_INTERNAL_LETTER_GRADES,
        }
        data.update(overrides)
        return data

    def test_save_blocked_without_prior_steps(self):
        self.school.setup.completed_steps = [
            SchoolSetup.SetupStep.SCHOOL_PROFILE,
        ]
        self.school.setup.save(update_fields=['completed_steps', 'updated_at'])

        response = self.client.put(self.url, self._letter_payload(), format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_save_creates_level_config_with_grade_bands(self):
        response = self.client.put(self.url, self._letter_payload(), format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['level_id'], str(self.level.id))
        self.assertEqual(response.data['config']['result_type'], 'grade_and_position')
        self.assertEqual(response.data['config']['grade_type'], 'letter')
        self.assertEqual(
            len(response.data['config']['grade_bands']),
            len(GES_INTERNAL_LETTER_GRADES),
        )
        self.assertTrue(
            AssessmentConfig.objects.filter(level=self.level).exists(),
        )

    def test_save_position_only_clears_grades(self):
        self.client.put(self.url, self._letter_payload(), format='json')

        response = self.client.put(
            self.url,
            {
                'continuous_assessment_weight': '30.00',
                'exam_weight': '70.00',
                'result_type': AssessmentConfig.ResultType.POSITION,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['config']['result_type'], 'position')
        self.assertIsNone(response.data['config']['grade_type'])
        self.assertEqual(response.data['config']['grade_bands'], [])
        self.assertEqual(response.data['config']['continuous_assessment_weight'], '30.00')

    def test_save_position_only_ignores_grade_fields(self):
        response = self.client.put(
            self.url,
            {
                'continuous_assessment_weight': '40.00',
                'exam_weight': '60.00',
                'result_type': AssessmentConfig.ResultType.POSITION,
                'grade_type': AssessmentConfig.GradeType.LETTER,
                'grade_bands': GES_INTERNAL_LETTER_GRADES,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['config']['result_type'], 'position')
        self.assertIsNone(response.data['config']['grade_type'])
        self.assertEqual(response.data['config']['grade_bands'], [])

    def test_save_rejects_weights_not_summing_to_100(self):
        response = self.client.put(
            self.url,
            self._letter_payload(
                continuous_assessment_weight='30.00',
                exam_weight='60.00',
            ),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('continuous_assessment_weight', response.data['raw_detail'])

    def test_save_rejects_overlapping_grade_bands(self):
        response = self.client.put(
            self.url,
            self._letter_payload(
                grade_bands=[
                    {'grade': 'A', 'min_score': 80, 'max_score': 100, 'remark': 'Excellent'},
                    {'grade': 'B', 'min_score': 70, 'max_score': 85, 'remark': 'Good'},
                    {'grade': 'F', 'min_score': 0, 'max_score': 69, 'remark': 'Fail'},
                ],
            ),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('grade_bands', response.data['raw_detail'])

    def test_save_rejects_inactive_level(self):
        self.level.is_active = False
        self.level.save(update_fields=['is_active', 'updated_at'])

        response = self.client.put(self.url, self._letter_payload(), format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_complete_blocked_when_level_missing_config(self):
        response = self.client.post(self.complete_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data['raw_detail'])

    def test_complete_advances_setup_when_all_active_levels_configured(self):
        second_level = Level.objects.create(
            school=self.school,
            name='Primary',
            order=2,
            is_system_generated=False,
        )
        Level.objects.create(
            school=self.school,
            name='Inactive Level',
            order=3,
            is_active=False,
            is_system_generated=False,
        )

        self.client.put(self.url, self._letter_payload(), format='json')
        self.client.put(
            reverse(
                'school-setup-assessment-level-config',
                kwargs={'level_id': second_level.id},
            ),
            {
                'continuous_assessment_weight': '50.00',
                'exam_weight': '50.00',
                'result_type': AssessmentConfig.ResultType.POSITION,
            },
            format='json',
        )

        response = self.client.post(self.complete_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['next_step'], 'fees')
        self.assertIn('assessment', response.data['completed_steps'])
