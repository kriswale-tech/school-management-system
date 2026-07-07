from django.test import TestCase

from academics.models import Curriculum, CurriculumClassLevel, CurriculumLevel, CurriculumSubject
from academics.services.curriculum import provision_school_curriculum, seed_ghana_curriculum
from accounts.tests.factories import create_school


class GhanaCurriculumTemplateTests(TestCase):
    def test_seed_creates_ghana_curriculum_structure(self):
        curriculum = seed_ghana_curriculum()

        self.assertEqual(curriculum.code, 'ghana')
        self.assertEqual(curriculum.version, '2024')
        pre_school = CurriculumLevel.objects.get(name='Pre-School')
        kindergarten = CurriculumLevel.objects.get(name='Kindergarten')
        self.assertEqual(pre_school.order, 1)
        self.assertEqual(kindergarten.order, 2)
        self.assertTrue(
            CurriculumClassLevel.objects.filter(level__name='Kindergarten', name='KG 1').exists(),
        )
        self.assertEqual(kindergarten.description, 'Kindergarten 1 & 2')
        self.assertTrue(
            CurriculumSubject.objects.filter(
                level__name='Junior High School',
                name='Mathematics',
                curriculum_class_level__isnull=True,
            ).exists(),
        )

    def test_seed_creates_class_scoped_preschool_subjects(self):
        seed_ghana_curriculum()

        creche_class = CurriculumClassLevel.objects.get(
            level__name='Pre-School',
            name='Crèche / Daycare (Ages 0-2)',
        )
        nursery_1 = CurriculumClassLevel.objects.get(
            level__name='Pre-School',
            name='Nursery 1',
        )

        self.assertTrue(
            CurriculumSubject.objects.filter(
                curriculum_class_level=creche_class,
                name='Sensory Stimulation (colors, sounds, textures)',
            ).exists(),
        )
        self.assertFalse(
            CurriculumSubject.objects.filter(
                curriculum_class_level=nursery_1,
                name='Sensory Stimulation (colors, sounds, textures)',
            ).exists(),
        )
        self.assertTrue(
            CurriculumSubject.objects.filter(
                curriculum_class_level=nursery_1,
                name='Pre-Literacy & Communication (phonics, letter recognition)',
            ).exists(),
        )

    def test_provision_creates_school_levels_classes_subjects(self):
        seed_ghana_curriculum()
        school = create_school()

        provision_school_curriculum(school)

        self.assertGreater(school.levels.count(), 0)
        self.assertGreater(school.class_levels.count(), 0)
        self.assertGreater(school.subjects.count(), 0)
        self.assertTrue(
            school.class_levels.filter(name='JHS 1').exists(),
        )
        self.assertTrue(
            school.class_levels.filter(streams__is_default=True).exists(),
        )
        jhs_1 = school.class_levels.get(name='JHS 1')
        self.assertEqual(jhs_1.description, 'JHS 1, 2 & 3')
        self.assertTrue(jhs_1.is_system_generated)
        self.assertIsNotNone(school.provisioned_curriculum_id)

    def test_provision_assigns_preschool_subjects_per_class(self):
        seed_ghana_curriculum()
        school = create_school()
        provision_school_curriculum(school)

        creche = school.class_levels.get(name='Crèche / Daycare (Ages 0-2)')
        nursery_1 = school.class_levels.get(name='Nursery 1')

        creche_subjects = set(creche.class_subjects.values_list('subject__name', flat=True))
        nursery_subjects = set(nursery_1.class_subjects.values_list('subject__name', flat=True))

        self.assertIn('Sensory Stimulation (colors, sounds, textures)', creche_subjects)
        self.assertNotIn('Sensory Stimulation (colors, sounds, textures)', nursery_subjects)
        self.assertIn('Pre-Literacy & Communication (phonics, letter recognition)', nursery_subjects)

    def test_provision_is_idempotent(self):
        seed_ghana_curriculum()
        school = create_school()

        provision_school_curriculum(school)
        level_count = school.levels.count()

        provision_school_curriculum(school)
        self.assertEqual(school.levels.count(), level_count)
