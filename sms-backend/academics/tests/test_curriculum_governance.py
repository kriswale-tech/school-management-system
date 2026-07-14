from django.core.exceptions import ValidationError
from django.test import TestCase

from academics.models import Level
from academics.services.custom_curriculum import (
    create_custom_class_level,
    create_custom_level,
    create_custom_subject,
    delete_custom_class_level,
    delete_custom_level,
)
from accounts.tests.factories import create_school
from academics.models import CurriculumLevel
from academics.services.curriculum import (
    GHANA_CURRICULUM_VERSION,
    provision_school_curriculum,
    seed_ghana_curriculum,
)


class CurriculumGovernanceTests(TestCase):
    def setUp(self):
        seed_ghana_curriculum()
        self.school = create_school()
        provision_school_curriculum(self.school)

    def test_provision_links_school_to_active_curriculum_version(self):
        self.school.refresh_from_db()

        self.assertIsNotNone(self.school.provisioned_curriculum)
        self.assertEqual(self.school.provisioned_curriculum.version, GHANA_CURRICULUM_VERSION)

    def test_provision_marks_records_as_system_generated_with_master_links(self):
        level = self.school.levels.get(name='Upper Primary')
        class_level = self.school.class_levels.get(name='Basic 4')
        subject = self.school.subjects.get(name='Ghanaian Language and Culture')

        self.assertTrue(level.is_system_generated)
        self.assertTrue(class_level.is_system_generated)
        self.assertTrue(subject.is_system_generated)
        self.assertIsNotNone(level.curriculum_level_id)
        self.assertIsNotNone(class_level.curriculum_class_level_id)

        class_subject = class_level.class_subjects.get(subject=subject)
        self.assertTrue(class_subject.is_system_generated)
        self.assertIsNotNone(class_subject.curriculum_subject_id)

        level_subject = level.level_subjects.get(subject=subject)
        self.assertTrue(level_subject.is_system_generated)
        self.assertIsNotNone(level_subject.curriculum_subject_id)

    def test_master_curriculum_is_immutable_outside_seed_context(self):
        template = CurriculumLevel.objects.get(name='Kindergarten')
        template.name = 'Changed'

        with self.assertRaises(ValidationError):
            template.save()

    def test_system_generated_level_cannot_be_deleted(self):
        level = self.school.levels.first()

        with self.assertRaises(ValidationError):
            level.delete()

    def test_system_generated_class_cannot_be_renamed(self):
        class_level = self.school.class_levels.first()
        class_level.name = 'Renamed'

        with self.assertRaises(ValidationError):
            class_level.save()

    def test_custom_level_and_class_can_be_created_and_deleted(self):
        custom_level = create_custom_level(
            self.school,
            name='Remedial',
            description='Extra support classes',
        )
        custom_class = create_custom_class_level(
            self.school,
            level=custom_level,
            name='Remedial 1',
        )
        custom_subject = create_custom_subject(self.school, name='Life Skills')

        self.assertFalse(custom_level.is_system_generated)
        self.assertFalse(custom_class.is_system_generated)
        self.assertFalse(custom_subject.is_system_generated)

        delete_custom_class_level(custom_class)
        delete_custom_level(custom_level)
        custom_subject.delete()

        self.assertFalse(Level.objects.filter(name='Remedial').exists())
