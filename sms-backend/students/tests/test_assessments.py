from datetime import date
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, ClassSubject, Level, LevelSubject, Subject
from accounts.models import User
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from assessments.models import (
    AssessmentConfig,
    AssessmentItem,
    AssessmentItemScore,
    StudentResult,
    SubjectScore,
)
from assessments.services import apply_grade_template
from schools.models import AcademicYear, Term
from students.tests.factories import create_student, enroll_student, ensure_default_stream
from teachers.models import ClassTeacher, TeachingAssignment


class StudentAssessmentViewTests(APITestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        set_client_auth_cookies(self.client, self.user)
        self.school = user_school(self.user)
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
        self.second_term = Term.objects.create(
            school=self.school,
            academic_year=self.academic_year,
            term=Term.TermChoices.SECOND_TERM,
            start_date=date(2026, 1, 8),
            end_date=date(2026, 4, 10),
            is_active=False,
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
            term=self.term,
            continuous_assessment_weight=Decimal('40'),
            exam_weight=Decimal('60'),
            result_type=AssessmentConfig.ResultType.GRADE_AND_POSITION,
            grade_type=AssessmentConfig.GradeType.LETTER,
        )
        apply_grade_template(self.config, AssessmentConfig.GradeType.LETTER)
        AssessmentConfig.objects.create(
            level=self.level,
            term=self.second_term,
            continuous_assessment_weight=Decimal('40'),
            exam_weight=Decimal('60'),
            result_type=AssessmentConfig.ResultType.GRADE_AND_POSITION,
            grade_type=AssessmentConfig.GradeType.LETTER,
        )

        self.teacher = create_user(
            is_active=True,
            phone_number='+233200000088',
            email='math-student-tab@test.com',
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
        ClassTeacher.objects.create(
            teacher=self.teacher,
            class_level=self.class_level,
            stream=self.stream,
            term=self.term,
        )
        self.student = create_student(
            school=self.school,
            student_id='STU-AS-001',
            first_name='Ada',
            last_name='Lovelace',
        )
        self.classmate = create_student(
            school=self.school,
            student_id='STU-AS-002',
            first_name='Grace',
            last_name='Hopper',
        )
        enroll_student(student=self.student, term=self.term, stream=self.stream)
        enroll_student(student=self.classmate, term=self.term, stream=self.stream)
        self.url = reverse('student-assessments', kwargs={'student_id': self.student.id})

    def _record_published(self, student, *, ca_mark, exam_mark):
        item = AssessmentItem.objects.create(
            teaching_assignment=self.assignment,
            name='Class test',
            max_marks=Decimal('50'),
            order=1,
        )
        AssessmentItemScore.objects.create(
            assessment_item=item,
            student=student,
            mark=Decimal(str(ca_mark)),
        )
        SubjectScore.objects.create(
            teaching_assignment=self.assignment,
            student=student,
            exam_mark=Decimal(str(exam_mark)),
            is_published=True,
            published_at=timezone.now(),
        )

    def test_returns_enrollment_terms_and_subject_row(self):
        self._record_published(self.student, ca_mark='40', exam_mark='70')
        StudentResult.objects.create(
            student=self.student,
            term=self.term,
            class_level=self.class_level,
            stream=self.stream,
            status=StudentResult.Status.RELEASED,
            remarks='Keep it up',
            conduct='Excellent',
            attitude='Positive',
            interest='Science',
            head_teacher_remarks='Well done',
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['enrolled'])
        self.assertEqual(str(response.data['term_id']), str(self.term.id))
        self.assertEqual(len(response.data['terms']), 1)
        self.assertEqual(response.data['class_teacher_name'], 'Math Tutor')
        self.assertEqual(response.data['weights']['continuous_assessment_weight'], 40.0)

        row = response.data['student']
        self.assertEqual(row['status'], 'released')
        self.assertEqual(row['class_teacher_remarks'], 'Keep it up')
        self.assertEqual(row['conduct'], 'Excellent')
        self.assertEqual(row['head_teacher_remarks'], 'Well done')
        self.assertEqual(len(row['subjects']), 1)
        subject = row['subjects'][0]
        self.assertEqual(subject['subject_name'], 'Mathematics')
        self.assertEqual(subject['teacher_name'], 'Math Tutor')
        self.assertEqual(subject['status'], 'Published')
        self.assertEqual(subject['class_score'], 32.0)
        self.assertEqual(subject['exam'], 70.0)
        self.assertIsNotNone(subject['grade'])

    def test_positions_are_relative_to_class_cohort(self):
        self._record_published(self.student, ca_mark='45', exam_mark='90')
        item = AssessmentItem.objects.get(teaching_assignment=self.assignment)
        AssessmentItemScore.objects.create(
            assessment_item=item,
            student=self.classmate,
            mark=Decimal('20'),
        )
        SubjectScore.objects.create(
            teaching_assignment=self.assignment,
            student=self.classmate,
            exam_mark=Decimal('50'),
            is_published=True,
            published_at=timezone.now(),
        )
        StudentResult.objects.create(
            student=self.student,
            term=self.term,
            class_level=self.class_level,
            stream=self.stream,
            status=StudentResult.Status.RELEASED,
        )
        StudentResult.objects.create(
            student=self.classmate,
            term=self.term,
            class_level=self.class_level,
            stream=self.stream,
            status=StudentResult.Status.RELEASED,
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = response.data['student']
        self.assertEqual(row['overall_position'], 1)
        self.assertEqual(row['overall_cohort_size'], 2)
        self.assertEqual(row['subjects'][0]['position'], 1)

    def test_term_without_enrollment_returns_empty_student(self):
        response = self.client.get(self.url, {'term': str(self.second_term.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['enrolled'])
        self.assertIsNone(response.data['student'])
        self.assertEqual(str(response.data['term_id']), str(self.second_term.id))
        self.assertEqual(len(response.data['terms']), 1)

    def test_unknown_student_returns_404(self):
        other = create_user(
            is_active=True,
            phone_number='+233200000099',
            email='other-school@test.com',
        )
        outsider = create_student(school=user_school(other), student_id='OUT-1')
        url = reverse('student-assessments', kwargs={'student_id': outsider.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_report_get_returns_404_when_missing(self):
        url = reverse('student-assessment-report', kwargs={'student_id': self.student.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_report_generate_requires_released_result(self):
        url = reverse(
            'student-assessment-report-generate',
            kwargs={'student_id': self.student.id},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_report_not_enrolled_term_returns_404(self):
        url = reverse('student-assessment-report', kwargs={'student_id': self.student.id})
        response = self.client.get(url, {'term': str(self.second_term.id)})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
