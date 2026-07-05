from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import SubjectGroup
from accounts.tests.factories import create_user, set_client_auth_cookies
from shared.services.curriculum import provision_school_curriculum, seed_ghana_curriculum


class SetupClassesAndSubjectsViewTests(APITestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        set_client_auth_cookies(self.client, self.user)
        self.school = self.user.school
        self.url = reverse('school-setup-classes-and-subjects')

    def test_get_returns_empty_levels_when_none_exist(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['levels'], [])

    def test_get_returns_levels_with_classes_streams_and_subjects(self):
        seed_ghana_curriculum()
        provision_school_curriculum(self.school)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        upper_primary = next(
            level for level in response.data['levels']
            if level['name'] == 'Upper Primary'
        )
        self.assertEqual(
            [class_level['name'] for class_level in upper_primary['classes']],
            ['Basic 4', 'Basic 5', 'Basic 6'],
        )
        self.assertTrue(
            all(class_level['streams'] for class_level in upper_primary['classes']),
        )

        subject_names = {subject['name'] for subject in upper_primary['subjects']}
        self.assertIn('Ghanaian Language and Culture', subject_names)
        self.assertIn('English Language', subject_names)

        ghanaian_language = next(
            subject for subject in upper_primary['subjects']
            if subject['name'] == 'Ghanaian Language and Culture'
        )
        self.assertEqual(ghanaian_language['groups'], [])

    def test_get_deduplicates_subject_groups_at_level_scope(self):
        seed_ghana_curriculum()
        provision_school_curriculum(self.school)

        upper_primary_class_subjects = self.school.class_subjects.filter(
            class_level__level__name='Upper Primary',
            subject__name='Ghanaian Language and Culture',
        )
        for class_subject in upper_primary_class_subjects:
            SubjectGroup.objects.create(class_subject=class_subject, name='Twi')
            SubjectGroup.objects.create(class_subject=class_subject, name='Ga')

        response = self.client.get(self.url)

        upper_primary = next(
            level for level in response.data['levels']
            if level['name'] == 'Upper Primary'
        )
        ghanaian_language = next(
            subject for subject in upper_primary['subjects']
            if subject['name'] == 'Ghanaian Language and Culture'
        )
        self.assertEqual(
            [group['name'] for group in ghanaian_language['groups']],
            ['Ga', 'Twi'],
        )
