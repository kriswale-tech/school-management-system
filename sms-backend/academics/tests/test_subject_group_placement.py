from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import (
    ClassLevel,
    ClassSubject,
    Level,
    LevelSubject,
    StudentSubjectGroup,
    Subject,
    SubjectGroup,
)
from accounts.models import User
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from schools.models import AcademicYear, Term
from students.tests.factories import create_student, enroll_student, ensure_default_stream
from teachers.models import TeachingAssignment


class SubjectGroupPlacementTests(APITestCase):
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
            name='Ghanaian Language',
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
        self.group_twi = SubjectGroup.objects.create(
            class_subject=self.class_subject,
            name='Twi',
        )
        self.group_ga = SubjectGroup.objects.create(
            class_subject=self.class_subject,
            name='Ga',
        )

        self.twi_teacher = create_user(
            is_active=True,
            phone_number='+233200000031',
            email='twi@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
            first_name='Twi',
            last_name='Tutor',
        )
        self.ga_teacher = create_user(
            is_active=True,
            phone_number='+233200000032',
            email='ga@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
            first_name='Ga',
            last_name='Tutor',
        )
        self.twi_assignment = TeachingAssignment.objects.create(
            teacher=self.twi_teacher,
            class_subject=self.class_subject,
            subject_group=self.group_twi,
            stream=self.stream,
            term=self.term,
        )
        self.ga_assignment = TeachingAssignment.objects.create(
            teacher=self.ga_teacher,
            class_subject=self.class_subject,
            subject_group=self.group_ga,
            stream=self.stream,
            term=self.term,
        )

        self.ada = create_student(
            school=self.school,
            student_id='GL-1',
            first_name='Ada',
            last_name='Mensah',
        )
        self.kofi = create_student(
            school=self.school,
            student_id='GL-2',
            first_name='Kofi',
            last_name='Owusu',
        )
        enroll_student(student=self.ada, term=self.term, stream=self.stream)
        enroll_student(student=self.kofi, term=self.term, stream=self.stream)

        self.candidates_url = reverse(
            'academics-subject-group-candidates',
            kwargs={'assignment_id': self.twi_assignment.id},
        )
        self.assign_url = reverse(
            'academics-subject-group-assign-students',
            kwargs={'assignment_id': self.twi_assignment.id},
        )
        self.unassign_url = reverse(
            'academics-subject-group-unassign-students',
            kwargs={'assignment_id': self.twi_assignment.id},
        )
        self.detail_url = reverse(
            'academics-teaching-assignment-detail',
            kwargs={'assignment_id': self.twi_assignment.id},
        )

    def test_candidates_mark_unassigned_and_detail_counts(self):
        set_client_auth_cookies(self.client, self.twi_teacher)

        detail = self.client.get(self.detail_url)
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertTrue(detail.data['is_grouped'])
        self.assertEqual(detail.data['students_count'], 0)
        self.assertEqual(detail.data['unassigned_students_count'], 2)

        candidates = self.client.get(self.candidates_url)
        self.assertEqual(candidates.status_code, status.HTTP_200_OK)
        self.assertEqual(candidates.data['unassigned_students_count'], 2)
        by_id = {row['id']: row for row in candidates.data['results']}
        self.assertEqual(by_id[str(self.ada.id)]['status'], 'unassigned')
        self.assertTrue(by_id[str(self.ada.id)]['selectable'])

    def test_assign_unassigned_then_block_cross_group_claim(self):
        set_client_auth_cookies(self.client, self.twi_teacher)
        assigned = self.client.post(
            self.assign_url,
            {'student_ids': [str(self.ada.id)]},
            format='json',
        )
        self.assertEqual(assigned.status_code, status.HTTP_200_OK)
        self.assertEqual(assigned.data['students_count'], 1)
        self.assertEqual(assigned.data['unassigned_students_count'], 1)
        self.assertTrue(
            StudentSubjectGroup.objects.filter(
                student=self.ada,
                subject_group=self.group_twi,
            ).exists()
        )

        set_client_auth_cookies(self.client, self.ga_teacher)
        ga_assign = reverse(
            'academics-subject-group-assign-students',
            kwargs={'assignment_id': self.ga_assignment.id},
        )
        blocked = self.client.post(
            ga_assign,
            {'student_ids': [str(self.ada.id)]},
            format='json',
        )
        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unassign_then_other_group_can_claim(self):
        StudentSubjectGroup.objects.create(
            student=self.ada,
            class_subject=self.class_subject,
            subject_group=self.group_twi,
            academic_year=self.academic_year,
        )
        set_client_auth_cookies(self.client, self.twi_teacher)
        removed = self.client.post(
            self.unassign_url,
            {'student_ids': [str(self.ada.id)]},
            format='json',
        )
        self.assertEqual(removed.status_code, status.HTTP_200_OK)
        self.assertFalse(
            StudentSubjectGroup.objects.filter(student=self.ada).exists()
        )

        set_client_auth_cookies(self.client, self.ga_teacher)
        ga_assign = reverse(
            'academics-subject-group-assign-students',
            kwargs={'assignment_id': self.ga_assignment.id},
        )
        claimed = self.client.post(
            ga_assign,
            {'student_ids': [str(self.ada.id)]},
            format='json',
        )
        self.assertEqual(claimed.status_code, status.HTTP_200_OK)
        self.assertEqual(claimed.data['students_count'], 1)
