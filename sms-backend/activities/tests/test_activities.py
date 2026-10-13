from datetime import date
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, Level
from accounts.models import User
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from activities.models import Activity
from fees.models import FeeItem, FeeStructure
from fees.services import apply_fee_structure, publish_fee_structure, record_student_payment
from schools.models import AcademicYear, Term
from students.tests.factories import create_student, enroll_student, ensure_default_stream


class ActivityFeedTests(APITestCase):
    def setUp(self):
        self.admin = create_user(is_active=True, role=User.RoleChoices.ADMIN)
        set_client_auth_cookies(self.client, self.admin)
        self.school = user_school(self.admin)
        self.academic_year = AcademicYear.objects.create(
            school=self.school,
            academic_year='2025/2026',
            start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31),
            is_active=True,
        )
        self.term = Term.objects.create(
            school=self.school,
            academic_year=self.academic_year,
            term=Term.TermChoices.FIRST_TERM,
            start_date=date(2025, 9, 1),
            end_date=date(2025, 12, 15),
            is_active=True,
        )
        self.level = Level.objects.create(
            school=self.school,
            name='Lower Primary',
            is_system_generated=False,
        )
        self.class_level = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='Primary 1',
            is_system_generated=False,
        )
        self.stream = ensure_default_stream(self.class_level)
        self.url = reverse('activity-list')

    def _apply_tuition(self):
        structure = FeeStructure.objects.create(
            school=self.school,
            term=self.term,
            created_by=self.admin,
        )
        FeeItem.objects.create(
            fee_structure=structure,
            name='Tuition Fee',
            amount=Decimal('200.00'),
            applies_to_type=FeeItem.AppliesToType.SCHOOL,
            student_type=FeeItem.StudentType.ALL_STUDENTS,
        )
        publish_fee_structure(structure)
        apply_fee_structure(structure)

    def test_payment_is_listed_for_admin(self):
        student = create_student(school=self.school, first_name='Kofi', last_name='Owusu')
        enroll_student(
            student=student,
            term=self.term,
            stream=self.stream,
            is_new_student=True,
        )
        self._apply_tuition()
        record_student_payment(
            school=self.school,
            student=student,
            amount=Decimal('200.00'),
            payment_method='cash',
            paid_at=timezone.now(),
            recorded_by=self.admin,
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        summaries = [row['summary'] for row in response.data['results']]
        self.assertTrue(any('Kofi Owusu' in summary for summary in summaries))
        self.assertTrue(
            Activity.objects.filter(
                school=self.school,
                verb=Activity.Verb.PAYMENT_RECORDED,
            ).exists()
        )

    def test_teacher_cannot_list_activities(self):
        teacher = create_user(
            is_active=True,
            role=User.RoleChoices.TEACHER,
            school=self.school,
            phone_number='+233201111111',
            email='teacher@test.com',
        )
        set_client_auth_cookies(self.client, teacher)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
