from django.test import TestCase

from accounts.tests.factories import create_school
from shared.models import Curriculum, CurriculumClassLevel, CurriculumLevel, CurriculumSubject
from shared.services.curriculum import provision_school_curriculum, seed_ghana_curriculum


class GhanaCurriculumTemplateTests(TestCase):
    def test_seed_creates_ghana_curriculum_structure(self):
        curriculum = seed_ghana_curriculum()

        self.assertEqual(curriculum.code, 'ghana')
        self.assertTrue(
            CurriculumLevel.objects.filter(curriculum=curriculum, name='Pre-School').exists(),
        )
        self.assertTrue(
            CurriculumClassLevel.objects.filter(level__name='Kindergarten', name='KG 1').exists(),
        )
        kindergarten = CurriculumLevel.objects.get(name='Kindergarten')
        self.assertEqual(kindergarten.description, 'Kindergarten 1 & 2')
        self.assertTrue(
            CurriculumSubject.objects.filter(
                level__name='Junior High School',
                name='Mathematics',
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

    def test_provision_is_idempotent(self):
        seed_ghana_curriculum()
        school = create_school()

        provision_school_curriculum(school)
        level_count = school.levels.count()

        provision_school_curriculum(school)
        self.assertEqual(school.levels.count(), level_count)
