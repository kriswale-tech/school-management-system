from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, Level
from accounts.models import User
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from assessments.models import StudentResult
from assessments.services.report import _serialize_school
from fees.models import FeeItem, FeeStructure, StudentFee
from schools.models import SchoolSettings, SchoolSetup
from schools.tests.factories import create_active_term
from students.services import generate_student_id
from students.tests.factories import create_student, enroll_student, ensure_default_stream
from teachers.models import ClassTeacher


class SchoolSettingsAPITests(APITestCase):
    def setUp(self):
        self.admin = create_user(is_active=True, email='admin@test.com')
        set_client_auth_cookies(self.client, self.admin)
        self.school = user_school(self.admin)
        self.school.setup_completed = True
        self.school.save(update_fields=['setup_completed', 'updated_at'])
        self.term = create_active_term(self.school)
        self.profile_url = reverse('school')
        self.settings_url = reverse('school-settings')
        self.alerts_url = reverse('school-alerts')

    def _as(self, user):
        set_client_auth_cookies(self.client, user, school=self.school)

    def test_admin_updates_profile_without_changing_setup(self):
        response = self.client.patch(
            self.profile_url,
            {
                'name': 'Updated Academy',
                'motto': 'Learn',
                'student_id_prefix': 'ua',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.school.refresh_from_db()
        self.assertEqual(self.school.name, 'Updated Academy')
        self.assertEqual(self.school.motto, 'Learn')
        self.assertEqual(self.school.student_id_prefix, 'UA')
        self.assertTrue(self.school.setup_completed)
        self.assertFalse(SchoolSetup.objects.filter(school=self.school).exists())

    def test_teacher_cannot_update_profile(self):
        teacher = create_user(
            phone_number='+233200000011',
            email='teacher@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
            is_active=True,
        )
        self._as(teacher)

        response = self.client.patch(
            self.profile_url,
            {'name': 'Nope'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.school.refresh_from_db()
        self.assertNotEqual(self.school.name, 'Nope')

    def test_rejects_short_student_id_prefix(self):
        response = self.client.patch(
            self.profile_url,
            {'student_id_prefix': 'A'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_student_id_uses_prefix(self):
        self.school.student_id_prefix = 'SMS'
        self.school.save(update_fields=['student_id_prefix', 'updated_at'])

        self.assertEqual(generate_student_id(school=self.school), 'SMS-0001')
        create_student(school=self.school, student_id='SMS-0001')
        self.assertEqual(generate_student_id(school=self.school), 'SMS-0002')

    def test_fee_and_enrollment_alerts_follow_role_and_switch(self):
        student = create_student(school=self.school, student_id='SET-0001')
        level = Level.objects.create(school=self.school, name='Junior High', is_system_generated=False)
        class_level = ClassLevel.objects.create(
            school=self.school,
            level=level,
            name='JHS 1',
            is_system_generated=False,
        )
        stream = ensure_default_stream(class_level)
        enrollment = enroll_student(
            student=student,
            term=self.term,
            stream=stream,
            is_new_student=True,
        )
        StudentResult.objects.create(
            student=student,
            term=self.term,
            class_level=enrollment.class_level,
            stream=stream,
            status=StudentResult.Status.RELEASED,
        )
        structure = FeeStructure.objects.create(
            school=self.school,
            term=self.term,
            created_by=self.admin,
        )
        item = FeeItem.objects.create(
            fee_structure=structure,
            name='Tuition',
            amount=Decimal('50.00'),
            applies_to_type=FeeItem.AppliesToType.SCHOOL,
        )
        StudentFee.objects.create(
            student=student,
            fee_structure=structure,
            fee_item=item,
            amount=Decimal('50.00'),
        )

        response = self.client.get(self.alerts_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        kinds = {item['kind'] for item in response.data}
        self.assertEqual(kinds, {'fees', 'enrollments'})

        accountant = create_user(
            phone_number='+233200000031',
            email='accounts@test.com',
            school=self.school,
            role=User.RoleChoices.ACCOUNTANT,
            is_active=True,
        )
        self._as(accountant)
        response = self.client.get(self.alerts_url)
        self.assertEqual([item['kind'] for item in response.data], ['fees'])

        self._as(self.admin)
        saved = self.client.patch(
            self.settings_url,
            {'fees_alert_enabled': False, 'enrollments_alert_enabled': False},
            format='json',
        )
        self.assertEqual(saved.status_code, status.HTTP_200_OK)
        response = self.client.get(self.alerts_url)
        self.assertEqual(response.data, [])

    def test_class_teacher_sees_unreleased_results_only(self):
        student = create_student(school=self.school, student_id='SET-0002')
        level = Level.objects.create(school=self.school, name='Primary', is_system_generated=False)
        class_level = ClassLevel.objects.create(
            school=self.school,
            level=level,
            name='Basic 1',
            is_system_generated=False,
        )
        stream = ensure_default_stream(class_level)
        enroll_student(student=student, term=self.term, stream=stream)
        StudentResult.objects.create(
            student=student,
            term=self.term,
            class_level=class_level,
            stream=stream,
            status=StudentResult.Status.APPROVED,
        )
        class_teacher = create_user(
            phone_number='+233200000041',
            email='class-teacher@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
            is_active=True,
        )
        ClassTeacher.objects.create(
            teacher=class_teacher,
            class_level=class_level,
            stream=stream,
            term=self.term,
        )
        plain_teacher = create_user(
            phone_number='+233200000042',
            email='plain-teacher@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
            is_active=True,
        )

        self._as(class_teacher)
        response = self.client.get(self.alerts_url)
        self.assertEqual([item['kind'] for item in response.data], ['results'])
        self.assertEqual(response.data[0]['count'], 1)

        self._as(plain_teacher)
        response = self.client.get(self.alerts_url)
        self.assertEqual(response.data, [])

    def test_report_card_hides_unchecked_fields(self):
        self.school.address = 'Adepa Loop'
        self.school.email = 'info@school.test'
        self.school.phone_number = '+233244567890'
        self.school.save(update_fields=['address', 'email', 'phone_number', 'updated_at'])
        SchoolSettings.objects.create(
            school=self.school,
            report_show_address=False,
            report_show_email=False,
            report_show_phones=True,
        )

        payload = _serialize_school(self.school)

        self.assertEqual(payload['name'], self.school.name)
        self.assertEqual(payload['address'], '')
        self.assertEqual(payload['email'], '')
        self.assertEqual(payload['phone_number'], '+233244567890')
