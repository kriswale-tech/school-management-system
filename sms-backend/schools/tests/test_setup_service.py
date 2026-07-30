from django.test import TestCase

from accounts.tests.factories import create_user, user_school
from schools.models import SchoolSetup
from schools.services.setup import require_prior_setup_steps
from schools.tests.factories import create_school_setup


class RequirePriorSetupStepsTests(TestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        self.school_setup = create_school_setup(user_school(self.user))

    def test_blocks_academic_year_step_without_school_profile(self):
        from rest_framework.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            require_prior_setup_steps(
                self.school_setup,
                SchoolSetup.SetupStep.ACADEMIC_YEAR_TERM,
            )

    def test_allows_academic_year_step_after_school_profile(self):
        self.school_setup.completed_steps = [SchoolSetup.SetupStep.SCHOOL_PROFILE]
        self.school_setup.save()

        require_prior_setup_steps(
            self.school_setup,
            SchoolSetup.SetupStep.ACADEMIC_YEAR_TERM,
        )
