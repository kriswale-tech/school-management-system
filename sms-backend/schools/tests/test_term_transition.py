from datetime import date, timedelta
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, ClassStream, Level
from accounts.models import User
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from fees.models import FeeItem, FeeStructure, StudentFee
from schools.models import AcademicYear, Term
from students.models import ClassEnrollment, Student
from students.services import create_class_enrollment
from students.tests.factories import create_student, enroll_student
from teachers.models import ClassTeacher


def _add_year(school, label, start, *, active_term='first_term'):
    first_end = start + timedelta(days=40)
    second_start = first_end + timedelta(days=1)
    second_end = second_start + timedelta(days=40)
    third_start = second_end + timedelta(days=1)
    third_end = third_start + timedelta(days=40)
    year = AcademicYear.objects.create(
        school=school,
        academic_year=label,
        start_date=start,
        end_date=third_end,
        is_active=active_term is not None,
    )
    terms = {}
    bounds = {
        'first_term': (start, first_end),
        'second_term': (second_start, second_end),
        'third_term': (third_start, third_end),
    }
    for key, (term_start, term_end) in bounds.items():
        terms[key] = Term.objects.create(
            school=school,
            academic_year=year,
            term=key,
            start_date=term_start,
            end_date=term_end,
            is_active=key == active_term,
        )
    return year, terms


def _classes(school, names):
    level = Level.objects.create(
        school=school,
        name='Upper Primary',
        order=1,
        is_system_generated=False,
    )
    created = []
    for index, name in enumerate(names, start=1):
        created.append(ClassLevel.objects.create(
            school=school,
            level=level,
            name=name,
            order=index,
            is_system_generated=False,
        ))
    return level, created


def _named_stream(class_level, name):
    return ClassStream.objects.create(
        class_level=class_level,
        name=name,
        is_default=False,
    )


def _school_fee(school, term, user, *, class_level=None):
    structure = FeeStructure.objects.create(
        school=school,
        term=term,
        created_by=user,
        status=FeeStructure.Status.DRAFT,
    )
    FeeItem.objects.create(
        fee_structure=structure,
        name='Class fee' if class_level else 'Tuition',
        amount=Decimal('100.00'),
        applies_to_type=(
            FeeItem.AppliesToType.CLASS if class_level else FeeItem.AppliesToType.SCHOOL
        ),
        applies_to_id=class_level.id if class_level else None,
        student_type=FeeItem.StudentType.ALL_STUDENTS,
    )
    structure.status = FeeStructure.Status.APPLIED
    structure.save(update_fields=['status', 'updated_at'])
    return structure


class TermTransitionTests(APITestCase):
    def setUp(self):
        self.admin = create_user(is_active=True, email='transition-admin@test.com')
        set_client_auth_cookies(self.client, self.admin)
        self.school = user_school(self.admin)
        self.confirm_url = reverse('school-transition-confirm')
        self.preview_url = reverse('school-transition-preview')
        self.status_url = reverse('school-transition-status')

    def test_same_year_keeps_the_class_and_copies_the_class_teacher(self):
        today = date.today()
        _year, terms = _add_year(self.school, '2026/2027', today - timedelta(days=10))
        _level, (basic4,) = _classes(self.school, ['Basic 4'])
        stream = _named_stream(basic4, 'A')
        student = create_student(school=self.school, student_id='B4-1')
        enroll_student(student=student, term=terms['first_term'], stream=stream)
        _school_fee(self.school, terms['first_term'], self.admin)
        teacher = create_user(
            phone_number='+233244567891',
            email='class-teacher@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
            is_active=True,
        )
        ClassTeacher.objects.create(
            teacher=teacher,
            class_level=basic4,
            stream=stream,
            term=terms['first_term'],
        )

        preview = self.client.get(self.preview_url)
        self.assertEqual(preview.status_code, status.HTTP_200_OK, preview.data)
        self.assertFalse(preview.data['is_year_change'])
        self.assertEqual(preview.data['placements'][0]['outcome'], 'stay')
        self.assertEqual(preview.data['placements'][0]['destination_stream_name'], 'A')

        response = self.client.post(
            self.confirm_url,
            {'acknowledge_warnings': True},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        enrollment = ClassEnrollment.objects.get(student=student, term=terms['second_term'])
        self.assertEqual(enrollment.stream_id, stream.id)
        self.assertFalse(enrollment.is_new_student)
        self.assertTrue(ClassTeacher.objects.filter(
            term=terms['second_term'],
            stream=stream,
            teacher=teacher,
        ).exists())
        self.assertTrue(terms['second_term'].__class__.objects.get(id=terms['second_term'].id).is_active)
        self.assertTrue(StudentFee.objects.filter(student=student, term=terms['second_term']).exists())

    def test_year_change_promotes_and_keeps_class_fees_on_their_class(self):
        today = date.today()
        _year, terms = _add_year(
            self.school,
            '2025/2026',
            today - timedelta(days=200),
            active_term='third_term',
        )
        _next, next_terms = _add_year(
            self.school,
            '2026/2027',
            terms['third_term'].end_date + timedelta(days=7),
            active_term=None,
        )
        _level, (basic4, basic5) = _classes(self.school, ['Basic 4', 'Basic 5'])
        source = _named_stream(basic4, 'A')
        _named_stream(basic5, 'A')
        student = create_student(school=self.school, student_id='B4-2')
        enroll_student(student=student, term=terms['third_term'], stream=source)
        _school_fee(self.school, terms['third_term'], self.admin, class_level=basic4)

        preview = self.client.get(self.preview_url)
        self.assertEqual(preview.status_code, status.HTTP_200_OK, preview.data)
        self.assertTrue(preview.data['is_year_change'])
        self.assertEqual(preview.data['placements'][0]['destination_class_name'], 'Basic 5')
        item = preview.data['fees']['items'][0]
        self.assertEqual(item['name'], 'Class fee')
        self.assertEqual(item['applies_to'], 'Basic 4')
        self.assertEqual(item['student_type'], 'All Students')

        response = self.client.post(
            self.confirm_url,
            {'acknowledge_warnings': True},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        enrollment = ClassEnrollment.objects.get(student=student, term=next_terms['first_term'])
        self.assertEqual(enrollment.class_level_id, basic5.id)
        self.assertEqual(enrollment.stream.name, 'A')
        self.assertFalse(StudentFee.objects.filter(
            student=student,
            term=next_terms['first_term'],
        ).exists())
        copied = FeeItem.objects.get(fee_structure__term=next_terms['first_term'])
        self.assertEqual(copied.applies_to_id, basic4.id)

    def test_stream_mismatch_waits_for_a_choice(self):
        today = date.today()
        _year, terms = _add_year(
            self.school,
            '2025/2026',
            today - timedelta(days=200),
            active_term='third_term',
        )
        _add_year(
            self.school,
            '2026/2027',
            terms['third_term'].end_date + timedelta(days=7),
            active_term=None,
        )
        _level, (basic4, basic5) = _classes(self.school, ['Basic 4', 'Basic 5'])
        source = _named_stream(basic4, 'A')
        destination = _named_stream(basic5, 'B')
        student = create_student(school=self.school, student_id='B4-3')
        enroll_student(student=student, term=terms['third_term'], stream=source)
        _school_fee(self.school, terms['third_term'], self.admin)

        preview = self.client.get(self.preview_url)
        self.assertEqual(preview.data['placements'][0]['outcome'], 'needs_stream')
        self.assertFalse(preview.data['can_confirm'])

        blocked = self.client.post(
            self.confirm_url,
            {'acknowledge_warnings': True},
            format='json',
        )
        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(
            self.confirm_url,
            {
                'acknowledge_warnings': True,
                'stream_choices': [{
                    'source_stream_id': str(source.id),
                    'destination_stream_id': str(destination.id),
                }],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        enrollment = ClassEnrollment.objects.get(student=student, term__term='first_term', term__academic_year__academic_year='2026/2027')
        self.assertEqual(enrollment.stream_id, destination.id)

    def test_last_class_is_marked_graduated_and_not_enrolled(self):
        today = date.today()
        _year, terms = _add_year(
            self.school,
            '2025/2026',
            today - timedelta(days=200),
            active_term='third_term',
        )
        _add_year(
            self.school,
            '2026/2027',
            terms['third_term'].end_date + timedelta(days=7),
            active_term=None,
        )
        _level, (jhs3,) = _classes(self.school, ['JHS 3'])
        stream = _named_stream(jhs3, 'A')
        student = create_student(school=self.school, student_id='J3-1')
        enroll_student(student=student, term=terms['third_term'], stream=stream)
        _school_fee(self.school, terms['third_term'], self.admin)

        response = self.client.post(
            self.confirm_url,
            {'acknowledge_warnings': True},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        student.refresh_from_db()
        self.assertTrue(student.is_graduated)
        self.assertFalse(student.enrollments.exclude(term=terms['third_term']).exists())

        cleared = self.client.post(reverse('student-clear-graduation', args=[student.id]))
        self.assertEqual(cleared.status_code, status.HTTP_200_OK, cleared.data)
        self.assertFalse(cleared.data['is_graduated'])
        student.refresh_from_db()
        self.assertFalse(ClassEnrollment.objects.filter(student=student).exclude(term=terms['third_term']).exists())

        student.is_graduated = True
        student.save(update_fields=['is_graduated', 'updated_at'])
        with self.assertRaises(Exception):
            create_class_enrollment(
                student=student,
                term=terms['third_term'],
                stream=stream,
            )

    def test_status_shows_inside_the_lead_window_only(self):
        today = date.today()
        _year, terms = _add_year(self.school, '2026/2027', today - timedelta(days=10))
        terms['first_term'].end_date = today + timedelta(days=3)
        terms['first_term'].save(update_fields=['end_date', 'updated_at'])
        visible = self.client.get(self.status_url)
        self.assertTrue(visible.data['visible'])
        self.assertEqual(visible.data['urgency'], 'red')

        Term.objects.filter(school=self.school, is_active=True).update(
            end_date=today + timedelta(days=40),
        )
        hidden = self.client.get(self.status_url)
        self.assertFalse(hidden.data['visible'])

    def test_inactive_student_is_left_behind(self):
        today = date.today()
        _year, terms = _add_year(self.school, '2026/2027', today - timedelta(days=10))
        _level, (basic4,) = _classes(self.school, ['Basic 4'])
        stream = _named_stream(basic4, 'A')
        student = create_student(school=self.school, student_id='IN-1')
        enroll_student(student=student, term=terms['first_term'], stream=stream)
        student.is_active = False
        student.save(update_fields=['is_active', 'updated_at'])
        _school_fee(self.school, terms['first_term'], self.admin)

        response = self.client.post(
            self.confirm_url,
            {'acknowledge_warnings': True},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertFalse(ClassEnrollment.objects.filter(
            student=student,
            term=terms['second_term'],
        ).exists())
        student.refresh_from_db()
        self.assertFalse(student.is_graduated)

    def test_active_unenrolled_student_blocks_transition(self):
        today = date.today()
        _add_year(self.school, '2026/2027', today - timedelta(days=10))
        _classes(self.school, ['Basic 4'])
        create_student(school=self.school, student_id='HANG-1')
        terms = {
            row.term: row
            for row in Term.objects.filter(school=self.school, academic_year__academic_year='2026/2027')
        }
        _school_fee(self.school, terms['first_term'], self.admin)

        preview = self.client.get(self.preview_url)
        self.assertEqual(preview.status_code, status.HTTP_200_OK, preview.data)
        self.assertFalse(preview.data['can_confirm'])
        self.assertTrue(
            any('not in a class' in blocker for blocker in preview.data['blockers']),
            preview.data['blockers'],
        )
        self.assertEqual(len(preview.data['unenrolled_students']), 1)

        response = self.client.post(
            self.confirm_url,
            {'acknowledge_warnings': True},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
