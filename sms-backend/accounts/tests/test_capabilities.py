from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import (
    ClassLevel,
    ClassStream,
    ClassSubject,
    Level,
    LevelSubject,
    Subject,
)
from accounts.capabilities import Capability
from accounts.models import User
from accounts.services.access_scope import resolve_access_scope
from accounts.services.capabilities import resolve_session_access
from accounts.tests.factories import (
    create_user,
    get_membership,
    set_client_auth_cookies,
    user_school,
)
from schools.models import AcademicYear, Term
from students.tests.factories import ensure_default_stream
from teachers.models import ClassTeacher, TeachingAssignment


class TeacherAccessCapabilitiesTests(APITestCase):
    def setUp(self):
        self.admin = create_user(is_active=True)
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
            name='Primary',
            is_system_generated=False,
        )
        self.class_level = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='Primary 1',
            is_system_generated=False,
        )
        ensure_default_stream(self.class_level)
        self.stream_a = ClassStream.objects.create(
            class_level=self.class_level,
            name='A',
            is_default=False,
        )
        self.stream_b = ClassStream.objects.create(
            class_level=self.class_level,
            name='B',
            is_default=False,
        )
        self.other_class = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='Primary 2',
            order=2,
            is_system_generated=False,
        )
        self.other_stream = ensure_default_stream(self.other_class)

        self.subject = Subject.objects.create(
            school=self.school,
            name='Math',
            is_system_generated=False,
        )
        LevelSubject.objects.create(
            school=self.school,
            level=self.level,
            subject=self.subject,
            is_system_generated=False,
        )
        self.class_subject = ClassSubject.objects.create(
            school=self.school,
            class_level=self.class_level,
            subject=self.subject,
            is_system_generated=False,
        )

        self.teacher = create_user(
            is_active=True,
            phone_number='+233200000011',
            email='teacher@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
            first_name='Ama',
            last_name='Teacher',
        )
        self.teacher_membership = get_membership(self.teacher, self.school)

        self.list_url = reverse('academics-classes')
        self.me_url = reverse('me')

    def test_admin_me_includes_school_wide_capabilities(self):
        set_client_auth_cookies(self.client, self.admin)
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(Capability.NAV_STUDENTS, response.data['capabilities'])
        self.assertIn(Capability.CLASSES_MANAGE, response.data['capabilities'])
        self.assertEqual(response.data['access']['mode'], 'school')

    def test_subject_teacher_capabilities_and_scoped_classes(self):
        TeachingAssignment.objects.create(
            teacher=self.teacher,
            class_subject=self.class_subject,
            stream=self.stream_a,
            term=self.term,
        )

        session = resolve_session_access(self.teacher_membership)
        self.assertTrue(session.has(Capability.ASSESSMENTS_RECORD))
        self.assertFalse(session.has(Capability.NAV_ASSESSMENTS))
        self.assertFalse(session.has(Capability.FEES_VIEW))
        self.assertFalse(session.has(Capability.NAV_STUDENTS))

        set_client_auth_cookies(self.client, self.teacher)
        me = self.client.get(self.me_url)
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertTrue(me.data['access']['is_subject_teacher'])
        self.assertFalse(me.data['access']['is_class_teacher'])
        self.assertEqual(me.data['access']['mode'], 'scoped')

        classes = self.client.get(self.list_url)
        self.assertEqual(classes.status_code, status.HTTP_200_OK)
        ids = {item['id'] for item in classes.data['results']}
        self.assertEqual(ids, {str(self.stream_a.id)})

    def test_class_teacher_capabilities_and_scoped_classes(self):
        ClassTeacher.objects.create(
            teacher=self.teacher,
            class_level=self.class_level,
            stream=self.stream_b,
            term=self.term,
        )

        session = resolve_session_access(self.teacher_membership)
        self.assertTrue(session.has(Capability.NAV_ASSESSMENTS))
        self.assertTrue(session.has(Capability.ASSESSMENTS_APPROVE))
        self.assertTrue(session.has(Capability.FEES_VIEW))
        self.assertFalse(session.has(Capability.ASSESSMENTS_RECORD))

        set_client_auth_cookies(self.client, self.teacher)
        classes = self.client.get(self.list_url)
        ids = {item['id'] for item in classes.data['results']}
        self.assertEqual(ids, {str(self.stream_b.id)})

    def test_whole_class_teacher_sees_all_streams_of_class(self):
        ClassTeacher.objects.create(
            teacher=self.teacher,
            class_level=self.class_level,
            stream=None,
            term=self.term,
        )

        scope = resolve_access_scope(self.teacher_membership)
        self.assertIn(self.stream_a.id, scope.visible_stream_ids)
        self.assertIn(self.stream_b.id, scope.visible_stream_ids)
        self.assertNotIn(self.other_stream.id, scope.visible_stream_ids)

        set_client_auth_cookies(self.client, self.teacher)
        classes = self.client.get(self.list_url)
        ids = {item['id'] for item in classes.data['results']}
        self.assertEqual(ids, {str(self.stream_a.id), str(self.stream_b.id)})

    def test_teacher_without_assignments_sees_no_classes(self):
        set_client_auth_cookies(self.client, self.teacher)
        classes = self.client.get(self.list_url)
        self.assertEqual(classes.status_code, status.HTTP_200_OK)
        self.assertEqual(classes.data['results'], [])
