from django.core.exceptions import ValidationError
from django.test import TestCase

from academics.models import CurriculumLevel, Level
from academics.services.curriculum import provision_school_curriculum, seed_ghana_curriculum
from academics.services.custom_curriculum import (
    assign_subject_to_class,
    create_custom_class_level,
    create_custom_subject,
)
from accounts.tests.factories import create_school


class FlexiblePreschoolLevelTests(TestCase):
    def setUp(self):
        seed_ghana_curriculum()
        self.school = create_school()
        provision_school_curriculum(self.school)

    def test_teachable_levels_have_unique_global_order(self):
        levels = list(self.school.levels.order_by('order', 'name').values_list('name', 'order'))

        self.assertEqual(levels, [
            ('Pre-School', 1),
            ('Kindergarten', 2),
            ('Lower Primary', 3),
            ('Upper Primary', 4),
            ('Junior High School', 5),
        ])

    def test_preschool_is_provisioned_with_default_classes_and_subjects(self):
        pre_school = self.school.levels.get(name='Pre-School')

        self.assertEqual(pre_school.subject_scope, Level.SubjectScope.CLASS)
        self.assertTrue(pre_school.allows_custom_classes)
        self.assertEqual(
            list(pre_school.class_levels.order_by('order').values_list('name', flat=True)),
            [
                'Crèche / Daycare (Ages 0-2)',
                'Nursery 1',
                'Nursery 2',
            ],
        )

        creche = pre_school.class_levels.get(name='Crèche / Daycare (Ages 0-2)')
        creche_subjects = set(creche.class_subjects.values_list('subject__name', flat=True))
        self.assertIn('Sensory Stimulation (colors, sounds, textures)', creche_subjects)

        nursery_1 = pre_school.class_levels.get(name='Nursery 1')
        nursery_subjects = set(nursery_1.class_subjects.values_list('subject__name', flat=True))
        self.assertIn('Pre-Literacy & Communication (phonics, letter recognition)', nursery_subjects)

    def test_ges_levels_still_provision_classes_and_subjects(self):
        kindergarten = self.school.levels.get(name='Kindergarten')

        self.assertEqual(kindergarten.subject_scope, Level.SubjectScope.LEVEL)
        self.assertFalse(kindergarten.allows_custom_classes)
        self.assertEqual(kindergarten.class_levels.count(), 2)
        self.assertGreater(kindergarten.class_levels.first().class_subjects.count(), 0)

    def test_custom_preschool_class_can_have_its_own_subjects(self):
        pre_school = self.school.levels.get(name='Pre-School')
        toddler_room = create_custom_class_level(
            self.school,
            level=pre_school,
            name='Toddler Room',
        )
        play = create_custom_subject(self.school, name='Play-based Learning')
        motor_skills = create_custom_subject(self.school, name='Motor Skills')

        assign_subject_to_class(self.school, class_level=toddler_room, subject=play)
        assign_subject_to_class(self.school, class_level=toddler_room, subject=motor_skills)

        subject_names = set(
            toddler_room.class_subjects.values_list('subject__name', flat=True),
        )
        self.assertEqual(subject_names, {'Play-based Learning', 'Motor Skills'})

    def test_assign_subject_to_class_blocked_for_ges_level(self):
        kg_1 = self.school.class_levels.get(name='KG 1')
        custom_subject = create_custom_subject(self.school, name='Extra Topic')

        with self.assertRaises(ValidationError):
            assign_subject_to_class(
                self.school,
                class_level=kg_1,
                subject=custom_subject,
            )

    def test_master_preschool_templates_are_marked_flexible(self):
        pre_school_template = CurriculumLevel.objects.get(name='Pre-School')
        kg_template = CurriculumLevel.objects.get(name='Kindergarten')

        self.assertEqual(pre_school_template.subject_scope, CurriculumLevel.SubjectScope.CLASS)
        self.assertTrue(pre_school_template.allows_custom_classes)
        self.assertEqual(kg_template.subject_scope, CurriculumLevel.SubjectScope.LEVEL)
