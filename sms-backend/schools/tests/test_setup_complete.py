from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from academics.models import ClassLevel, Level
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from fees.models import FeeItem, FeeStructure, StudentFee
from schools.models import AcademicYear, SchoolSetup, Term
from schools.services.setup import (
    REQUIRED_SETUP_STEPS,
    advance_setup_step,
    complete_school_setup,
    validate_setup_ready,
)
from schools.tests.factories import create_school_setup
from students.tests.factories import create_student, enroll_student, ensure_default_stream


class AdvanceSetupStepTests(APITestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        self.school = user_school(self.user)
        self.school_setup = create_school_setup(self.school)

    def test_completing_all_required_steps_does_not_finalize_setup(self):
        for step in REQUIRED_SETUP_STEPS:
            result = advance_setup_step(self.school_setup, step)
            self.school_setup.refresh_from_db()
            self.school.refresh_from_db()

        self.assertEqual(result['next_step'], SchoolSetup.SetupStep.STAFF)
        self.assertFalse(result['is_complete'])
        self.assertEqual(result['progress_percentage'], 100)
        self.assertFalse(self.school.setup_completed)
        self.assertIsNone(self.school.setup_completed_at)


class ValidateSetupReadyTests(APITestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        self.school = user_school(self.user)
        academic_year = AcademicYear.objects.create(
            school=self.school,
            academic_year='2025/2026',
            start_date='2025-09-01',
            end_date='2026-07-31',
            is_active=True,
        )
        Term.objects.create(
            school=self.school,
            academic_year=academic_year,
            term=Term.TermChoices.FIRST_TERM,
            start_date='2025-09-01',
            end_date='2025-12-15',
            is_active=True,
        )
        self.school_setup = create_school_setup(
            self.school,
            completed_steps=[step.value for step in REQUIRED_SETUP_STEPS],
            current_step=SchoolSetup.SetupStep.STAFF,
        )

    def test_rejects_when_required_steps_missing(self):
        self.school_setup.completed_steps = [
            SchoolSetup.SetupStep.SCHOOL_PROFILE,
        ]
        self.school_setup.save()

        with self.assertRaises(ValidationError) as exc:
            validate_setup_ready(self.school, self.school_setup)

        self.assertIn('missing_steps', exc.exception.detail)

    @patch('schools.services.teachers.validate_teachers_setup_ready')
    @patch('schools.services.fees.validate_fees_setup_ready')
    @patch('schools.services.assessment.validate_assessment_setup_ready')
    @patch('schools.services.classes_and_subjects.validate_classes_and_subjects_ready')
    def test_delegates_to_step_validators(
        self,
        mock_classes,
        mock_assessment,
        mock_fees,
        mock_teachers,
    ):
        validate_setup_ready(self.school, self.school_setup)

        mock_classes.assert_called_once_with(self.school)
        mock_assessment.assert_called_once_with(self.school)
        mock_fees.assert_called_once_with(self.school)
        mock_teachers.assert_called_once_with(self.school)


class CompleteSchoolSetupServiceTests(APITestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        self.school = user_school(self.user)
        self.school_setup = create_school_setup(
            self.school,
            completed_steps=[step.value for step in REQUIRED_SETUP_STEPS],
            current_step=SchoolSetup.SetupStep.STAFF,
        )

    @patch('schools.services.fees.apply_active_term_fees')
    @patch('schools.services.setup.validate_setup_ready')
    def test_marks_school_setup_complete(self, mock_validate, mock_apply_fees):
        result = complete_school_setup(self.school)

        self.school.refresh_from_db()
        self.school_setup.refresh_from_db()
        mock_validate.assert_called_once_with(self.school, self.school_setup)
        mock_apply_fees.assert_called_once_with(self.school)
        self.assertTrue(result['is_complete'])
        self.assertEqual(result['next_step'], SchoolSetup.SetupStep.COMPLETED)
        self.assertEqual(result['progress_percentage'], 100)
        self.assertTrue(self.school.setup_completed)
        self.assertIsNotNone(self.school.setup_completed_at)
        self.assertEqual(
            self.school_setup.current_step,
            SchoolSetup.SetupStep.COMPLETED,
        )

    def test_rejects_when_already_complete(self):
        self.school.setup_completed = True
        self.school.save(update_fields=['setup_completed', 'updated_at'])

        with self.assertRaises(ValidationError):
            complete_school_setup(self.school)

    @patch('schools.services.setup.validate_setup_ready')
    def test_applies_active_term_fees_on_complete(self, mock_validate):
        academic_year = AcademicYear.objects.create(
            school=self.school,
            academic_year='2025/2026',
            start_date='2025-09-01',
            end_date='2026-07-31',
            is_active=True,
        )
        term = Term.objects.create(
            school=self.school,
            academic_year=academic_year,
            term=Term.TermChoices.FIRST_TERM,
            start_date='2025-09-01',
            end_date='2025-12-15',
            is_active=True,
        )
        level = Level.objects.create(
            school=self.school,
            name='Junior High',
            is_system_generated=False,
        )
        class_level = ClassLevel.objects.create(
            school=self.school,
            level=level,
            name='JHS 1',
            is_system_generated=False,
        )
        stream = ensure_default_stream(class_level)
        student = create_student(
            school=self.school,
            student_id='TA-0001',
            first_name='Ama',
            last_name='Mensah',
        )
        enroll_student(
            student=student,
            term=term,
            stream=stream,
            is_new_student=True,
        )

        structure = FeeStructure.objects.create(
            school=self.school,
            term=term,
            created_by=self.user,
        )
        FeeItem.objects.create(
            fee_structure=structure,
            name='Tuition Fee',
            amount=Decimal('500.00'),
            applies_to_type=FeeItem.AppliesToType.SCHOOL,
            student_type=FeeItem.StudentType.ALL_STUDENTS,
        )

        complete_school_setup(self.school)

        structure.refresh_from_db()
        self.assertEqual(structure.status, FeeStructure.Status.APPLIED)
        self.assertEqual(StudentFee.objects.filter(student=student).count(), 1)
        self.assertEqual(
            StudentFee.objects.get(student=student).amount,
            Decimal('500.00'),
        )


class CompleteSetupViewTests(APITestCase):
    def setUp(self):
        self.admin = create_user(is_active=True)
        set_client_auth_cookies(self.client, self.admin)
        self.school = user_school(self.admin)
        self.url = reverse('school-setup-complete')

    @patch('schools.setup_views.complete.complete_school_setup')
    def test_post_delegates_to_service(self, mock_complete):
        mock_complete.return_value = {
            'next_step': SchoolSetup.SetupStep.COMPLETED,
            'completed_steps': [step.value for step in REQUIRED_SETUP_STEPS],
            'is_complete': True,
            'progress_percentage': 100,
        }

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_complete.assert_called_once_with(self.school)
        self.assertTrue(response.data['is_complete'])

    def test_post_rejects_when_already_complete(self):
        self.school.setup_completed = True
        self.school.save(update_fields=['setup_completed', 'updated_at'])

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
