from datetime import date

from django.test import TestCase

from academics.models import StudentSubjectGroup, SubjectGroup
from accounts.tests.factories import create_school
from schools.models import AcademicYear
from academics.services.curriculum import provision_school_curriculum, seed_ghana_curriculum
from students.models import Student


class SubjectGroupTests(TestCase):
    def setUp(self):
        seed_ghana_curriculum()
        self.school = create_school()
        provision_school_curriculum(self.school)
        self.class_subject = self.school.class_subjects.get(
            subject__name='Ghanaian Language and Culture',
            class_level__name='Basic 4',
        )
        self.academic_year = AcademicYear.objects.create(
            school=self.school,
            academic_year='2026/2027',
            start_date=date(2026, 9, 1),
            end_date=date(2027, 7, 31),
            is_active=True,
        )

    def test_subject_groups_can_be_created_for_class_subject(self):
        twi = SubjectGroup.objects.create(
            class_subject=self.class_subject,
            name='Twi',
        )
        ga = SubjectGroup.objects.create(
            class_subject=self.class_subject,
            name='Ga',
        )

        self.assertEqual(self.class_subject.groups.count(), 2)
        self.assertEqual(twi.name, 'Twi')
        self.assertEqual(ga.name, 'Ga')

    def test_student_can_be_assigned_to_one_group_per_class_subject_per_year(self):
        twi = SubjectGroup.objects.create(
            class_subject=self.class_subject,
            name='Twi',
        )
        student = Student.objects.create()

        assignment = StudentSubjectGroup.objects.create(
            student=student,
            subject_group=twi,
            academic_year=self.academic_year,
        )

        self.assertEqual(assignment.class_subject_id, self.class_subject.id)
        self.assertEqual(assignment.subject_group_id, twi.id)

    def test_class_subject_is_synced_from_subject_group(self):
        twi = SubjectGroup.objects.create(
            class_subject=self.class_subject,
            name='Twi',
        )
        student = Student.objects.create()

        assignment = StudentSubjectGroup.objects.create(
            student=student,
            subject_group=twi,
            academic_year=self.academic_year,
        )

        self.assertEqual(assignment.class_subject_id, twi.class_subject_id)
