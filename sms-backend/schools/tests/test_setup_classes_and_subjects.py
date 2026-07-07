from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import SubjectGroup
from academics.services.custom_curriculum import create_custom_class_level, create_custom_subject
from academics.services.custom_curriculum import assign_subject_to_class
from accounts.tests.factories import create_user, set_client_auth_cookies
from academics.services.curriculum import provision_school_curriculum, seed_ghana_curriculum


class SetupClassesAndSubjectsViewTests(APITestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        set_client_auth_cookies(self.client, self.user)
        self.school = self.user.school
        self.url = reverse('school-setup-classes-and-subjects')

    def test_get_returns_empty_array_when_none_exist(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_returns_levels_with_classes_streams_and_subjects(self):
        seed_ghana_curriculum()
        provision_school_curriculum(self.school)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        upper_primary = next(
            level for level in response.data
            if level['name'] == 'Upper Primary'
        )
        self.assertEqual(
            [class_level['name'] for class_level in upper_primary['classes']],
            ['Basic 4', 'Basic 5', 'Basic 6'],
        )
        self.assertTrue(
            all(class_level['streams'] for class_level in upper_primary['classes']),
        )
        self.assertTrue(
            all(class_level['subjects'] for class_level in upper_primary['classes']),
        )
        self.assertFalse(upper_primary['classes'][0]['is_editable'])

        subject_names = {subject['name'] for subject in upper_primary['subjects']}
        self.assertIn('Ghanaian Language and Culture', subject_names)
        self.assertIn('English Language', subject_names)

        ghanaian_language = next(
            subject for subject in upper_primary['subjects']
            if subject['name'] == 'Ghanaian Language and Culture'
        )
        self.assertEqual(ghanaian_language['groups'], [])
        self.assertFalse(ghanaian_language['is_editable'])

        class_subject = upper_primary['classes'][0]['subjects'][0]
        self.assertIn('class_subject_id', class_subject)
        self.assertFalse(class_subject['is_editable'])

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
            level for level in response.data
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

    def test_get_returns_preschool_with_per_class_subjects_and_distinct_level_subjects(self):
        seed_ghana_curriculum()
        provision_school_curriculum(self.school)

        response = self.client.get(self.url)

        pre_school = next(level for level in response.data if level['name'] == 'Pre-School')
        self.assertEqual(pre_school['subject_scope'], 'class')
        self.assertTrue(pre_school['allows_custom_classes'])
        self.assertEqual(
            [class_level['name'] for class_level in pre_school['classes']],
            [
                'Crèche / Daycare (Ages 0-2)',
                'Nursery 1',
                'Nursery 2',
            ],
        )

        creche = next(
            class_level for class_level in pre_school['classes']
            if class_level['name'] == 'Crèche / Daycare (Ages 0-2)'
        )
        nursery_1 = next(
            class_level for class_level in pre_school['classes']
            if class_level['name'] == 'Nursery 1'
        )
        self.assertGreater(len(creche['subjects']), 0)
        self.assertGreater(len(nursery_1['subjects']), 0)
        self.assertFalse(creche['is_editable'])

        level_subject_names = {subject['name'] for subject in pre_school['subjects']}
        self.assertIn('Sensory Stimulation (colors, sounds, textures)', level_subject_names)
        self.assertIn('Pre-Literacy & Communication (phonics, letter recognition)', level_subject_names)

    def test_custom_class_and_subject_are_editable_in_response(self):
        seed_ghana_curriculum()
        provision_school_curriculum(self.school)

        pre_school = self.school.levels.get(name='Pre-School')
        custom_class = create_custom_class_level(self.school, level=pre_school, name='Toddler Room')
        custom_subject = create_custom_subject(self.school, name='Play-based Learning')
        assign_subject_to_class(self.school, class_level=custom_class, subject=custom_subject)

        response = self.client.get(self.url)
        pre_school_payload = next(level for level in response.data if level['name'] == 'Pre-School')
        toddler_room = next(
            class_level for class_level in pre_school_payload['classes']
            if class_level['name'] == 'Toddler Room'
        )
        play_subject = next(
            subject for subject in toddler_room['subjects']
            if subject['name'] == 'Play-based Learning'
        )

        self.assertTrue(toddler_room['is_editable'])
        self.assertTrue(play_subject['is_editable'])
