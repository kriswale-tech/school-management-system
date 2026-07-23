from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import SubjectGroup
from academics.services.curriculum import provision_school_curriculum, seed_ghana_curriculum
from accounts.models import User
from accounts.tests.factories import create_user, set_client_auth_cookies
from schools.models import AcademicYear, SchoolSetup, Term
from schools.tests.factories import create_school_setup
from teachers.models import ClassTeacher, TeachingAssignment


class SetupTeacherAssignmentViewTests(APITestCase):
    def setUp(self):
        self.admin = create_user(is_active=True)
        set_client_auth_cookies(self.client, self.admin)
        self.school = self.admin.school
        seed_ghana_curriculum()
        provision_school_curriculum(self.school)
        self.academic_year = AcademicYear.objects.create(
            school=self.school,
            academic_year='2025/2026',
            start_date='2025-09-01',
            end_date='2026-07-31',
            is_active=True,
        )
        self.term = Term.objects.create(
            school=self.school,
            academic_year=self.academic_year,
            term=Term.TermChoices.FIRST_TERM,
            start_date='2025-09-01',
            end_date='2025-12-15',
            is_active=True,
        )
        create_school_setup(
            self.school,
            completed_steps=[
                SchoolSetup.SetupStep.SCHOOL_PROFILE,
                SchoolSetup.SetupStep.ACADEMIC_YEAR_TERM,
                SchoolSetup.SetupStep.CLASSES_AND_SUBJECTS,
                SchoolSetup.SetupStep.ASSESSMENT,
                SchoolSetup.SetupStep.FEES,
            ],
            current_step=SchoolSetup.SetupStep.TEACHERS,
        )
        self.teacher = create_user(
            phone_number='+233244567891',
            email='teacher@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
            is_active=True,
            first_name='Ama',
            last_name='Boateng',
        )
        self.class_level = self.school.class_levels.get(name='Basic 4')
        self.class_subject = self.school.class_subjects.filter(
            class_level=self.class_level,
            subject__name='Mathematics',
        ).first()
        self.teachers_url = reverse('school-setup-teachers')
        self.class_teacher_url = reverse('school-setup-class-teacher-assignments')
        self.teaching_assignment_url = reverse('school-setup-teaching-assignments')

    def test_create_class_teacher_assignment_for_whole_class(self):
        response = self.client.post(
            self.class_teacher_url,
            {
                'teacher_id': str(self.teacher.id),
                'class_level_id': str(self.class_level.id),
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['class_level_id'], str(self.class_level.id))
        self.assertIsNone(response.data['stream_id'])
        self.assertTrue(
            ClassTeacher.objects.filter(
                teacher=self.teacher,
                class_level=self.class_level,
                term=self.term,
                stream__isnull=True,
            ).exists(),
        )

    def test_create_teaching_assignment_for_class_subject(self):
        response = self.client.post(
            self.teaching_assignment_url,
            {
                'teacher_id': str(self.teacher.id),
                'class_subject_id': str(self.class_subject.id),
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['class_subject_id'], str(self.class_subject.id))
        self.assertEqual(response.data['subject_name'], 'Mathematics')
        self.assertIsNone(response.data['stream_id'])
        self.assertIsNone(response.data['subject_group_id'])

    def test_create_teaching_assignment_for_stream(self):
        stream_response = self.client.post(
            reverse('school-setup-class-streams', kwargs={'class_id': self.class_level.id}),
            {'name': 'B'},
            format='json',
        )
        stream_id = stream_response.data['id']

        response = self.client.post(
            self.teaching_assignment_url,
            {
                'teacher_id': str(self.teacher.id),
                'class_subject_id': str(self.class_subject.id),
                'stream_id': stream_id,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['stream_id'], stream_id)
        self.assertEqual(response.data['stream_name'], 'B')

    def test_create_teaching_assignment_for_subject_group(self):
        subject_group = SubjectGroup.objects.create(
            class_subject=self.class_subject,
            name='Elective A',
        )

        response = self.client.post(
            self.teaching_assignment_url,
            {
                'teacher_id': str(self.teacher.id),
                'class_subject_id': str(self.class_subject.id),
                'subject_group_id': str(subject_group.id),
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['subject_group_id'], str(subject_group.id))
        self.assertEqual(response.data['subject_group_name'], 'Elective A')

    def test_duplicate_class_teacher_slot_is_rejected(self):
        payload = {
            'teacher_id': str(self.teacher.id),
            'class_level_id': str(self.class_level.id),
        }
        first_response = self.client.post(self.class_teacher_url, payload, format='json')
        second_response = self.client.post(self.class_teacher_url, payload, format='json')

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_teaching_assignment(self):
        create_response = self.client.post(
            self.teaching_assignment_url,
            {
                'teacher_id': str(self.teacher.id),
                'class_subject_id': str(self.class_subject.id),
            },
            format='json',
        )
        assignment_id = create_response.data['id']

        delete_response = self.client.delete(
            reverse(
                'school-setup-teaching-assignment-detail',
                kwargs={'assignment_id': assignment_id},
            ),
        )

        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TeachingAssignment.objects.filter(id=assignment_id).exists())

    def test_teacher_list_includes_created_assignments(self):
        self.client.post(
            self.class_teacher_url,
            {
                'teacher_id': str(self.teacher.id),
                'class_level_id': str(self.class_level.id),
            },
            format='json',
        )
        self.client.post(
            self.teaching_assignment_url,
            {
                'teacher_id': str(self.teacher.id),
                'class_subject_id': str(self.class_subject.id),
            },
            format='json',
        )

        response = self.client.get(self.teachers_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        teacher = next(
            item for item in response.data['results'] if item['id'] == str(self.teacher.id)
        )
        self.assertEqual(len(teacher['class_teacher_assignments']), 1)
        self.assertEqual(len(teacher['teaching_assignments']), 1)


class CompleteTeachersSetupViewTests(APITestCase):
    def setUp(self):
        self.admin = create_user(is_active=True)
        set_client_auth_cookies(self.client, self.admin)
        self.school = self.admin.school
        self.academic_year = AcademicYear.objects.create(
            school=self.school,
            academic_year='2025/2026',
            start_date='2025-09-01',
            end_date='2026-07-31',
            is_active=True,
        )
        Term.objects.create(
            school=self.school,
            academic_year=self.academic_year,
            term=Term.TermChoices.FIRST_TERM,
            start_date='2025-09-01',
            end_date='2025-12-15',
            is_active=True,
        )
        create_school_setup(
            self.school,
            completed_steps=[
                SchoolSetup.SetupStep.SCHOOL_PROFILE,
                SchoolSetup.SetupStep.ACADEMIC_YEAR_TERM,
                SchoolSetup.SetupStep.CLASSES_AND_SUBJECTS,
                SchoolSetup.SetupStep.ASSESSMENT,
                SchoolSetup.SetupStep.FEES,
            ],
            current_step=SchoolSetup.SetupStep.TEACHERS,
        )
        self.complete_url = reverse('school-setup-teachers-complete')

    def test_complete_requires_at_least_one_teacher(self):
        response = self.client.post(self.complete_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_complete_advances_setup(self):
        create_user(
            phone_number='+233244567891',
            email='teacher@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
            is_active=True,
        )

        response = self.client.post(self.complete_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['next_step'], 'staff')
        self.assertIn('teachers', response.data['completed_steps'])
        self.assertFalse(response.data['is_complete'])
        self.assertEqual(response.data['progress_percentage'], 100)
