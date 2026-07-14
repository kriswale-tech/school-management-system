from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import SubjectGroup
from academics.services.curriculum import provision_school_curriculum, seed_ghana_curriculum
from accounts.tests.factories import create_user, set_client_auth_cookies
from schools.models import SchoolSetup
from schools.tests.factories import create_school_setup


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
            all(class_level['subjects'] for class_level in upper_primary['classes']),
        )
        self.assertTrue(
            all(class_level['streams'] == [] for class_level in upper_primary['classes']),
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
        response = self.client.post(
            reverse('school-setup-custom-classes', kwargs={'level_id': pre_school.id}),
            {'name': 'Toddler Room'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        custom_class_id = response.data['id']

        subject_response = self.client.post(
            reverse('school-setup-subjects'),
            {
                'level_id': str(pre_school.id),
                'name': 'Play-based Learning',
                'class_ids': [str(custom_class_id)],
            },
            format='json',
        )
        self.assertEqual(subject_response.status_code, status.HTTP_201_CREATED)

        listing = self.client.get(self.url)
        pre_school_payload = next(level for level in listing.data if level['name'] == 'Pre-School')
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


class SetupClassesAndSubjectsMutationTests(APITestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        set_client_auth_cookies(self.client, self.user)
        self.school = self.user.school
        seed_ghana_curriculum()
        provision_school_curriculum(self.school)
        create_school_setup(
            self.school,
            completed_steps=[
                SchoolSetup.SetupStep.SCHOOL_PROFILE,
                SchoolSetup.SetupStep.ACADEMIC_YEAR_TERM,
            ],
            current_step=SchoolSetup.SetupStep.CLASSES_AND_SUBJECTS,
        )

    def test_stream_crud(self):
        basic_4 = self.school.class_levels.get(name='Basic 4')

        create_response = self.client.post(
            reverse('school-setup-class-streams', kwargs={'class_id': basic_4.id}),
            {'name': 'A'},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        stream_id = create_response.data['id']
        self.assertEqual(create_response.data['name'], 'A')
        self.assertFalse(create_response.data['is_default'])

        listing = self.client.get(reverse('school-setup-classes-and-subjects'))
        basic_4_payload = next(
            class_level
            for level in listing.data if level['name'] == 'Upper Primary'
            for class_level in level['classes'] if class_level['name'] == 'Basic 4'
        )
        self.assertEqual(
            [stream['name'] for stream in basic_4_payload['streams']],
            ['A'],
        )
        self.assertTrue(all(not stream['is_default'] for stream in basic_4_payload['streams']))

        patch_response = self.client.patch(
            reverse('school-setup-stream-detail', kwargs={'stream_id': stream_id}),
            {'name': 'B'},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.data['name'], 'B')

        delete_response = self.client.delete(
            reverse('school-setup-stream-detail', kwargs={'stream_id': stream_id}),
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        default_stream = basic_4.streams.get(is_default=True)
        blocked = self.client.delete(
            reverse('school-setup-stream-detail', kwargs={'stream_id': default_stream.id}),
        )
        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST)

    def test_subject_group_crud_replicates_for_level_scope(self):
        class_subject = self.school.class_subjects.get(
            class_level__name='Basic 4',
            subject__name='Ghanaian Language and Culture',
        )
        level = class_subject.class_level.level
        subject = class_subject.subject

        create_response = self.client.post(
            reverse(
                'school-setup-subject-groups',
                kwargs={'level_id': level.id, 'subject_id': subject.id},
            ),
            {'name': 'Twi'},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            SubjectGroup.objects.filter(
                class_subject__subject=subject,
                class_subject__class_level__level=level,
                name='Twi',
            ).count(),
            3,
        )

        group_id = create_response.data['id']
        patch_response = self.client.patch(
            reverse('school-setup-group-detail', kwargs={'group_id': group_id}),
            {'name': 'Asante Twi'},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            SubjectGroup.objects.filter(
                class_subject__subject=subject,
                name='Asante Twi',
            ).count(),
            3,
        )

        self.client.post(
            reverse(
                'school-setup-subject-groups',
                kwargs={'level_id': level.id, 'subject_id': subject.id},
            ),
            {'name': 'Ga'},
            format='json',
        )
        delete_response = self.client.delete(
            reverse('school-setup-group-detail', kwargs={'group_id': group_id}),
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            SubjectGroup.objects.filter(
                class_subject__subject=subject,
                name='Asante Twi',
            ).exists(),
        )

    def test_subject_group_applies_only_to_classes_with_subject_for_class_scope(self):
        pre_school = self.school.levels.get(name='Pre-School')
        nursery_1 = pre_school.class_levels.get(name='Nursery 1')
        nursery_2 = pre_school.class_levels.get(name='Nursery 2')
        subject_response = self.client.post(
            reverse('school-setup-subjects'),
            {
                'level_id': str(pre_school.id),
                'name': 'Language Choice',
                'class_ids': [str(nursery_1.id), str(nursery_2.id)],
            },
            format='json',
        )
        self.assertEqual(subject_response.status_code, status.HTTP_201_CREATED)
        subject_id = subject_response.data['id']

        create_response = self.client.post(
            reverse(
                'school-setup-subject-groups',
                kwargs={'level_id': pre_school.id, 'subject_id': subject_id},
            ),
            {'name': 'Twi'},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            SubjectGroup.objects.filter(
                class_subject__subject_id=subject_id,
                name='Twi',
            ).count(),
            2,
        )
        self.assertFalse(
            SubjectGroup.objects.filter(
                class_subject__class_level__name='Crèche / Daycare (Ages 0-2)',
                name='Twi',
            ).exists(),
        )

    def test_custom_class_and_subject_for_preschool(self):
        pre_school = self.school.levels.get(name='Pre-School')
        nursery_1 = pre_school.class_levels.get(name='Nursery 1')

        class_response = self.client.post(
            reverse('school-setup-custom-classes', kwargs={'level_id': pre_school.id}),
            {'name': 'Toddler Room'},
            format='json',
        )
        self.assertEqual(class_response.status_code, status.HTTP_201_CREATED)
        class_id = class_response.data['id']
        self.assertTrue(class_response.data['is_editable'])
        self.assertEqual(class_response.data['order'], 4)
        self.assertEqual(class_response.data['streams'], [])

        insert_response = self.client.post(
            reverse('school-setup-custom-classes', kwargs={'level_id': pre_school.id}),
            {'name': 'Playgroup', 'order': 2},
            format='json',
        )
        self.assertEqual(insert_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(insert_response.data['order'], 2)
        orders = list(
            pre_school.class_levels.order_by('order').values_list('name', 'order'),
        )
        self.assertEqual(
            orders,
            [
                ('Crèche / Daycare (Ages 0-2)', 1),
                ('Playgroup', 2),
                ('Nursery 1', 3),
                ('Nursery 2', 4),
                ('Toddler Room', 5),
            ],
        )

        subject_response = self.client.post(
            reverse('school-setup-subjects'),
            {
                'level_id': str(pre_school.id),
                'name': 'Play-based Learning',
                'class_ids': [str(class_id), str(nursery_1.id)],
            },
            format='json',
        )
        self.assertEqual(subject_response.status_code, status.HTTP_201_CREATED)
        subject_id = subject_response.data['id']
        self.assertEqual(len(subject_response.data['class_ids']), 2)

        update_response = self.client.patch(
            reverse('school-setup-subject-detail', kwargs={'subject_id': subject_id}),
            {'name': 'Play Learning', 'class_ids': [str(class_id)]},
            format='json',
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data['name'], 'Play Learning')
        self.assertEqual(update_response.data['class_ids'], [class_id])

        remove_response = self.client.delete(
            reverse(
                'school-setup-class-subject-assignment',
                kwargs={'class_id': class_id, 'subject_id': subject_id},
            ),
        )
        self.assertEqual(remove_response.status_code, status.HTTP_204_NO_CONTENT)

        recreate = self.client.post(
            reverse('school-setup-subjects'),
            {
                'level_id': str(pre_school.id),
                'name': 'Motor Skills',
                'class_ids': [str(class_id)],
            },
            format='json',
        )
        self.assertEqual(recreate.status_code, status.HTTP_201_CREATED)

        delete_class = self.client.delete(
            reverse('school-setup-class-detail', kwargs={'class_id': class_id}),
        )
        self.assertEqual(delete_class.status_code, status.HTTP_204_NO_CONTENT)

    def test_can_remove_and_reassign_system_subject_on_preschool_class(self):
        nursery_1 = self.school.class_levels.get(name='Nursery 1')
        toddler = self.client.post(
            reverse(
                'school-setup-custom-classes',
                kwargs={'level_id': nursery_1.level_id},
            ),
            {'name': 'Toddler Room'},
            format='json',
        )
        self.assertEqual(toddler.status_code, status.HTTP_201_CREATED)
        toddler_id = toddler.data['id']

        class_subject = self.school.class_subjects.get(
            class_level=nursery_1,
            subject__name='Pre-Literacy & Communication (phonics, letter recognition)',
        )
        subject = class_subject.subject
        self.assertTrue(class_subject.is_system_generated)

        remove_response = self.client.delete(
            reverse(
                'school-setup-class-subject-assignment',
                kwargs={'class_id': nursery_1.id, 'subject_id': subject.id},
            ),
        )
        self.assertEqual(remove_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            self.school.class_subjects.filter(
                class_level=nursery_1,
                subject=subject,
            ).exists(),
        )

        listing = self.client.get(reverse('school-setup-classes-and-subjects'))
        pre_school_payload = next(
            level for level in listing.data if level['name'] == 'Pre-School'
        )
        still_listed = next(
            item for item in pre_school_payload['subjects']
            if str(item['id']) == str(subject.id)
        )
        self.assertNotIn(str(nursery_1.id), [str(cid) for cid in still_listed['class_ids']])
        self.assertIn(str(subject.id), [str(item['id']) for item in pre_school_payload['subjects']])

        reassign_response = self.client.patch(
            reverse('school-setup-subject-detail', kwargs={'subject_id': subject.id}),
            {'class_ids': [str(toddler_id)]},
            format='json',
        )
        self.assertEqual(reassign_response.status_code, status.HTTP_200_OK)
        self.assertEqual(reassign_response.data['class_ids'], [toddler_id])
        self.assertTrue(
            self.school.class_subjects.filter(
                class_level_id=toddler_id,
                subject=subject,
            ).exists(),
        )

    def test_assign_subject_to_class_post_and_duplicate_error(self):
        pre_school = self.school.levels.get(name='Pre-School')
        nursery_1 = pre_school.class_levels.get(name='Nursery 1')
        toddler = self.client.post(
            reverse('school-setup-custom-classes', kwargs={'level_id': pre_school.id}),
            {'name': 'Toddler Room'},
            format='json',
        )
        toddler_id = toddler.data['id']
        subject = self.school.class_subjects.get(
            class_level=nursery_1,
            subject__name='Pre-Literacy & Communication (phonics, letter recognition)',
        ).subject

        assign_url = reverse(
            'school-setup-class-subject-assignment',
            kwargs={'class_id': toddler_id, 'subject_id': subject.id},
        )
        response = self.client.post(assign_url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(str(response.data['id']), str(subject.id))
        self.assertIn('class_subject_id', response.data)

        duplicate = self.client.post(assign_url)
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already assigned', str(duplicate.data['raw_detail']).lower())

        blocked = self.client.post(
            reverse(
                'school-setup-class-subject-assignment',
                kwargs={
                    'class_id': self.school.class_levels.get(name='Basic 4').id,
                    'subject_id': self.school.subjects.filter(
                        name='English Language',
                    ).first().id,
                },
            ),
        )
        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST)

    def test_level_scoped_subject_assigns_all_classes(self):
        upper_primary = self.school.levels.get(name='Upper Primary')

        response = self.client.post(
            reverse('school-setup-subjects'),
            {
                'level_id': str(upper_primary.id),
                'name': 'Creative Arts Extra',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['class_ids']), 3)

    def test_activation_endpoints(self):
        level = self.school.levels.get(name='Kindergarten')
        class_level = level.class_levels.get(name='KG 1')
        subject = self.school.subjects.filter(name='English Language').first()

        level_response = self.client.patch(
            reverse('school-setup-level-status', kwargs={'level_id': level.id}),
            {'is_active': False},
            format='json',
        )
        self.assertEqual(level_response.status_code, status.HTTP_200_OK)
        self.assertFalse(level_response.data['is_active'])

        class_response = self.client.patch(
            reverse('school-setup-class-status', kwargs={'class_id': class_level.id}),
            {'is_active': False},
            format='json',
        )
        self.assertEqual(class_response.status_code, status.HTTP_200_OK)
        self.assertFalse(class_response.data['is_active'])

        subject_response = self.client.patch(
            reverse('school-setup-subject-status', kwargs={'subject_id': subject.id}),
            {'is_active': False},
            format='json',
        )
        self.assertEqual(subject_response.status_code, status.HTTP_200_OK)
        self.assertFalse(subject_response.data['is_active'])

    def test_complete_blocked_when_single_custom_stream(self):
        basic_4 = self.school.class_levels.get(name='Basic 4')
        self.client.post(
            reverse('school-setup-class-streams', kwargs={'class_id': basic_4.id}),
            {'name': 'A'},
            format='json',
        )

        response = self.client.post(reverse('school-setup-classes-and-subjects-complete'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data['raw_detail'])

    def test_complete_advances_setup(self):
        response = self.client.post(reverse('school-setup-classes-and-subjects-complete'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['next_step'], 'assessment')
        self.assertIn('classes_and_subjects', response.data['completed_steps'])
