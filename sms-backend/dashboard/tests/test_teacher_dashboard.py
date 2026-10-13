from datetime import date
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, ClassSubject, Level, LevelSubject, Subject, SubjectGroup
from assessments.models import AssessmentItem, AssessmentItemScore, SubjectScore
from accounts.models import User
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from activities.models import Activity
from activities.services import record_activity
from fees.models import FeeItem, FeeStructure
from fees.services import apply_fee_structure, publish_fee_structure, record_student_payment
from schools.models import AcademicYear, Term
from students.tests.factories import create_student, enroll_student, ensure_default_stream
from teachers.models import ClassTeacher, TeachingAssignment


class TeacherDashboardViewTests(APITestCase):
    def setUp(self):
        self.admin = create_user(is_active=True, role=User.RoleChoices.ADMIN)
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
        self.teacher = create_user(
            is_active=True,
            role=User.RoleChoices.TEACHER,
            school=self.school,
            phone_number='+233201010101',
            email='class.teacher@test.com',
            first_name='Ama',
            last_name='Boateng',
        )
        self.url = reverse('dashboard-teacher')

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

    def test_class_teacher_sees_their_class_and_payment(self):
        ClassTeacher.objects.create(
            teacher=self.teacher,
            class_level=self.class_level,
            stream=self.stream,
            term=self.term,
        )
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
            amount=Decimal('50.00'),
            payment_method='cash',
            paid_at=timezone.now(),
            recorded_by=self.admin,
        )

        set_client_auth_cookies(self.client, self.teacher)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_class_teacher'])
        self.assertEqual(response.data['classes_overview']['classes_count'], 1)
        self.assertEqual(response.data['classes_overview']['students_count'], 1)
        self.assertEqual(response.data['classes'][0]['display_name'], self.stream.full_name)
        self.assertNotIn('fees_overview', response.data)
        self.assertNotIn('top_debtors', response.data)
        summaries = [row['summary'] for row in response.data['activities']]
        self.assertTrue(any('Kofi Owusu enrolled' in summary for summary in summaries))
        self.assertFalse(any('Payment of GHS' in summary for summary in summaries))

    def test_subject_teacher_sees_only_their_subject_activity(self):
        subject = Subject.objects.create(
            school=self.school,
            name='Mathematics',
            is_system_generated=False,
        )
        LevelSubject.objects.create(
            school=self.school,
            level=self.level,
            subject=subject,
            is_system_generated=False,
        )
        class_subject = ClassSubject.objects.create(
            school=self.school,
            class_level=self.class_level,
            subject=subject,
            is_system_generated=False,
        )
        own = TeachingAssignment.objects.create(
            teacher=self.teacher,
            class_subject=class_subject,
            stream=self.stream,
            term=self.term,
        )
        other_teacher = create_user(
            is_active=True,
            role=User.RoleChoices.TEACHER,
            school=self.school,
            phone_number='+233202020202',
            email='other.teacher@test.com',
            first_name='Yaw',
            last_name='Mensah',
        )
        other_subject = Subject.objects.create(
            school=self.school,
            name='English',
            is_system_generated=False,
        )
        LevelSubject.objects.create(
            school=self.school,
            level=self.level,
            subject=other_subject,
            is_system_generated=False,
        )
        other_class_subject = ClassSubject.objects.create(
            school=self.school,
            class_level=self.class_level,
            subject=other_subject,
            is_system_generated=False,
        )
        other = TeachingAssignment.objects.create(
            teacher=other_teacher,
            class_subject=other_class_subject,
            stream=self.stream,
            term=self.term,
        )
        record_activity(
            school=self.school,
            actor=self.teacher,
            verb=Activity.Verb.SCORES_PUBLISHED,
            summary='Ama Boateng published Mathematics scores.',
            term=self.term,
            stream=self.stream,
            teaching_assignment=own,
        )
        record_activity(
            school=self.school,
            actor=other_teacher,
            verb=Activity.Verb.SCORES_PUBLISHED,
            summary='Yaw Mensah published English scores.',
            term=self.term,
            stream=self.stream,
            teaching_assignment=other,
        )

        set_client_auth_cookies(self.client, self.teacher)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_subject_teacher'])
        summaries = [row['summary'] for row in response.data['activities']]
        self.assertIn('Ama Boateng published Mathematics scores.', summaries)
        self.assertNotIn('Yaw Mensah published English scores.', summaries)

    def _math_assignment(self):
        subject = Subject.objects.create(
            school=self.school,
            name='Mathematics',
            is_system_generated=False,
        )
        LevelSubject.objects.create(
            school=self.school,
            level=self.level,
            subject=subject,
            is_system_generated=False,
        )
        class_subject = ClassSubject.objects.create(
            school=self.school,
            class_level=self.class_level,
            subject=subject,
            is_system_generated=False,
        )
        return TeachingAssignment.objects.create(
            teacher=self.teacher,
            class_subject=class_subject,
            stream=self.stream,
            term=self.term,
        )

    def test_publish_prompt_waits_for_a_complete_result(self):
        assignment = self._math_assignment()
        student = create_student(school=self.school, first_name='Ada', last_name='Mensah')
        enroll_student(student=student, term=self.term, stream=self.stream, is_new_student=True)

        set_client_auth_cookies(self.client, self.teacher)
        quiet = self.client.get(self.url)
        labels = [item['label'] for item in quiet.data['needs_attention']]
        self.assertFalse(any(label.startswith('Publish ') for label in labels))

        item = AssessmentItem.objects.create(
            teaching_assignment=assignment,
            name='Class test',
            max_marks=Decimal('20'),
            order=1,
        )
        AssessmentItemScore.objects.create(
            assessment_item=item,
            student=student,
            mark=Decimal('16'),
        )
        SubjectScore.objects.create(
            teaching_assignment=assignment,
            student=student,
            exam_mark=Decimal('70'),
            is_published=False,
        )

        ready = self.client.get(self.url)
        labels = [item['label'] for item in ready.data['needs_attention']]
        self.assertTrue(any('Publish Mathematics scores' in label for label in labels))

    def test_group_teacher_is_asked_to_place_unassigned_students(self):
        assignment = self._math_assignment()
        group = SubjectGroup.objects.create(class_subject=assignment.class_subject, name='Group A')
        assignment.subject_group = group
        assignment.stream = None
        assignment.save()
        student = create_student(school=self.school, first_name='Kojo', last_name='Mensah')
        enroll_student(student=student, term=self.term, stream=self.stream, is_new_student=True)

        set_client_auth_cookies(self.client, self.teacher)
        response = self.client.get(self.url)
        labels = [item['label'] for item in response.data['needs_attention']]
        self.assertTrue(any('Place 1 student in Group A' in label for label in labels))
        self.assertFalse(any(label.startswith('Publish ') for label in labels))

    def test_admin_cannot_load_teacher_dashboard(self):
        set_client_auth_cookies(self.client, self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
