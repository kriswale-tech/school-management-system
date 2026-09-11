from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, ClassSubject, Level, LevelSubject, Subject
from accounts.models import User
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from assessments.models import AssessmentConfig, AssessmentItem, AssessmentItemScore
from assessments.services import apply_grade_template
from schools.models import AcademicYear, Term
from students.tests.factories import create_student, enroll_student, ensure_default_stream
from teachers.models import TeachingAssignment


class SubjectAssessmentWorkspaceApiTests(APITestCase):
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
            name='JHS',
            is_system_generated=False,
        )
        self.class_level = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='JHS 1',
            is_system_generated=False,
        )
        self.stream = ensure_default_stream(self.class_level)
        self.subject = Subject.objects.create(
            school=self.school,
            name='Mathematics',
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

        self.config = AssessmentConfig.objects.create(
            level=self.level,
            continuous_assessment_weight=Decimal('40'),
            exam_weight=Decimal('60'),
            result_type=AssessmentConfig.ResultType.GRADE_AND_POSITION,
            grade_type=AssessmentConfig.GradeType.LETTER,
        )
        apply_grade_template(self.config, AssessmentConfig.GradeType.LETTER)

        self.teacher = create_user(
            is_active=True,
            phone_number='+233200000041',
            email='math@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
            first_name='Math',
            last_name='Tutor',
        )
        self.assignment = TeachingAssignment.objects.create(
            teacher=self.teacher,
            class_subject=self.class_subject,
            stream=self.stream,
            term=self.term,
        )
        self.student = create_student(school=self.school, first_name='Ada', last_name='Lovelace')
        enroll_student(student=self.student, term=self.term, stream=self.stream)

        self.workspace_url = reverse(
            'academics-teaching-assignment-workspace',
            kwargs={'assignment_id': self.assignment.id},
        )
        self.ca_items_url = reverse(
            'academics-teaching-assignment-ca-items',
            kwargs={'assignment_id': self.assignment.id},
        )
        self.marks_url = reverse(
            'academics-teaching-assignment-marks',
            kwargs={'assignment_id': self.assignment.id},
        )

    def test_workspace_returns_setup_weights(self):
        set_client_auth_cookies(self.client, self.teacher)
        response = self.client.get(self.workspace_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['weights']['continuous_assessment_weight'], 40.0)
        self.assertEqual(response.data['weights']['exam_weight'], 60.0)
        self.assertEqual(len(response.data['students']), 1)
        self.assertEqual(response.data['students'][0]['status'], 'Incomplete')

    def test_create_ca_item_and_save_marks_without_exam(self):
        set_client_auth_cookies(self.client, self.teacher)
        created = self.client.post(
            self.ca_items_url,
            {'name': 'Homework 1', 'max_marks': '20'},
            format='json',
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        item_id = str(created.data['id'])

        saved = self.client.put(
            self.marks_url,
            {
                'students': [
                    {
                        'student_id': str(self.student.id),
                        'ca': {item_id: '16'},
                        'exam': None,
                    },
                ],
            },
            format='json',
        )
        self.assertEqual(saved.status_code, status.HTTP_200_OK)
        row = saved.data['students'][0]
        self.assertEqual(row['ca'][item_id], 16.0)
        self.assertIsNone(row['exam'])
        self.assertEqual(row['class_score'], 32.0)  # 80% of 40
        self.assertEqual(row['status'], 'Incomplete')

    def test_save_with_exam_reaches_complete(self):
        set_client_auth_cookies(self.client, self.teacher)
        item = AssessmentItem.objects.create(
            teaching_assignment=self.assignment,
            name='Class test',
            max_marks=Decimal('50'),
            order=1,
        )
        response = self.client.put(
            self.marks_url,
            {
                'students': [
                    {
                        'student_id': str(self.student.id),
                        'ca': {str(item.id): '40'},
                        'exam': '70',
                    },
                ],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = response.data['students'][0]
        self.assertEqual(row['status'], 'Complete')
        self.assertIsNotNone(row['grade'])
        self.assertIsNotNone(row['total'])

    def test_publish_and_unpublish_complete_student(self):
        set_client_auth_cookies(self.client, self.teacher)
        item = AssessmentItem.objects.create(
            teaching_assignment=self.assignment,
            name='Class test',
            max_marks=Decimal('50'),
            order=1,
        )
        self.client.put(
            self.marks_url,
            {
                'students': [
                    {
                        'student_id': str(self.student.id),
                        'ca': {str(item.id): '40'},
                        'exam': '70',
                    },
                ],
            },
            format='json',
        )
        publish_url = reverse(
            'academics-teaching-assignment-publish',
            kwargs={'assignment_id': self.assignment.id},
        )
        published = self.client.post(
            publish_url,
            {'student_ids': [str(self.student.id)]},
            format='json',
        )
        self.assertEqual(published.status_code, status.HTTP_200_OK)
        self.assertEqual(published.data['students'][0]['status'], 'Published')

        unpublish_url = reverse(
            'academics-teaching-assignment-unpublish',
            kwargs={'assignment_id': self.assignment.id},
        )
        unpublished = self.client.post(
            unpublish_url,
            {'student_ids': [str(self.student.id)]},
            format='json',
        )
        self.assertEqual(unpublished.status_code, status.HTTP_200_OK)
        self.assertEqual(unpublished.data['students'][0]['status'], 'Complete')

    def test_cannot_delete_ca_item_with_marks(self):
        set_client_auth_cookies(self.client, self.teacher)
        item = AssessmentItem.objects.create(
            teaching_assignment=self.assignment,
            name='Midterm',
            max_marks=Decimal('50'),
            order=1,
        )
        AssessmentItemScore.objects.create(
            assessment_item=item,
            student=self.student,
            mark=Decimal('40'),
        )
        url = reverse(
            'academics-teaching-assignment-ca-item-detail',
            kwargs={'assignment_id': self.assignment.id, 'item_id': item.id},
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
