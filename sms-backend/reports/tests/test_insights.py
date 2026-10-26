from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, ClassSubject, Level, LevelSubject, Subject
from accounts.models import User
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from assessments.models import AssessmentConfig, AssessmentItem, AssessmentItemScore, SubjectScore
from assessments.services import apply_grade_template
from schools.models import AcademicYear, Term
from students.tests.factories import create_student, enroll_student, ensure_default_stream
from teachers.models import ClassTeacher, TeachingAssignment


class ReportsInsightsApiTests(APITestCase):
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
            term=self.term,
            continuous_assessment_weight=Decimal('40'),
            exam_weight=Decimal('60'),
            result_type=AssessmentConfig.ResultType.GRADE_AND_POSITION,
            grade_type=AssessmentConfig.GradeType.LETTER,
        )
        apply_grade_template(self.config, AssessmentConfig.GradeType.LETTER)

        self.teacher = create_user(
            is_active=True,
            phone_number='+233200000091',
            email='reports-math@test.com',
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

        item = AssessmentItem.objects.create(
            teaching_assignment=self.assignment,
            name='CA1',
            max_marks=Decimal('100'),
            order=1,
        )
        AssessmentItemScore.objects.create(
            assessment_item=item,
            student=self.student,
            mark=Decimal('80'),
        )
        SubjectScore.objects.create(
            teaching_assignment=self.assignment,
            student=self.student,
            exam_mark=Decimal('70'),
            is_published=True,
        )

        self.overview_url = reverse('reports-overview')
        self.by_class_url = reverse('reports-by-class')
        self.by_subject_url = reverse('reports-by-subject')
        self.grade_url = reverse('reports-grade-distribution')
        self.trends_url = reverse('reports-student-trends')
        self.filters_url = reverse('reports-filters')
        self.heatmap_url = reverse('reports-subject-heatmap')
        self.workflow_url = reverse('reports-workflow')
        self.teacher_desk_url = reverse('reports-teacher-desk')
        self.staff_capacity_url = reverse('reports-staff-capacity')
        self.performance_url = reverse(
            'student-performance',
            kwargs={'student_id': self.student.id},
        )

    def test_admin_overview_includes_published_scores(self):
        set_client_auth_cookies(self.client, self.admin)
        response = self.client.get(self.overview_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['students_count'], 1)
        self.assertEqual(response.data['students_with_results'], 1)
        self.assertEqual(response.data['published_subject_scores'], 1)
        self.assertIsNotNone(response.data['average_score'])
        self.assertGreater(response.data['average_score'], 0)
        self.assertEqual(response.data['pass_mark'], 40.0)
        self.assertEqual(response.data['classes_count'], 1)
        self.assertEqual(response.data['distinct_subjects_count'], 1)
        self.assertEqual(response.data['class_subjects_count'], 1)
        self.assertEqual(response.data['teaching_assignments_count'], 1)
        self.assertEqual(response.data['unassigned_class_subjects'], 0)

    def test_overview_uses_configured_pass_mark(self):
        self.config.pass_mark = Decimal('55.00')
        self.config.save(update_fields=['pass_mark', 'updated_at'])

        set_client_auth_cookies(self.client, self.admin)
        response = self.client.get(self.overview_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['pass_mark'], 55.0)

    def test_by_class_and_subject_return_rows(self):
        set_client_auth_cookies(self.client, self.admin)
        by_class = self.client.get(self.by_class_url)
        by_subject = self.client.get(self.by_subject_url)
        grades = self.client.get(
            self.grade_url,
            {'class_level_id': str(self.class_level.id)},
        )
        trends = self.client.get(self.trends_url)

        self.assertEqual(by_class.status_code, status.HTTP_200_OK)
        self.assertEqual(len(by_class.data['results']), 1)
        self.assertEqual(by_class.data['results'][0]['display_name'], 'JHS 1')
        self.assertEqual(by_class.data['results'][0]['students_count'], 1)
        self.assertEqual(by_class.data['results'][0]['students_with_results'], 1)
        self.assertEqual(by_class.data['students_count'], 1)

        self.assertEqual(by_subject.status_code, status.HTTP_200_OK)
        self.assertEqual(by_subject.data['results'][0]['subject_name'], 'Mathematics')

        self.assertEqual(grades.status_code, status.HTTP_200_OK)
        self.assertEqual(grades.data['mode'], 'grades')
        self.assertEqual(grades.data['class_level_name'], 'JHS 1')
        self.assertEqual(grades.data['students_count'], 1)
        self.assertEqual(grades.data['students_with_results'], 1)
        self.assertGreater(grades.data['total_graded'], 0)

        self.assertEqual(trends.status_code, status.HTTP_200_OK)
        self.assertEqual(trends.data['students_count'], 1)
        self.assertEqual(len(trends.data['top_students']), 1)

    def test_subject_teacher_can_access_scoped_reports(self):
        set_client_auth_cookies(self.client, self.teacher)
        response = self.client.get(self.overview_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['scope_mode'], 'scoped')
        self.assertEqual(response.data['students_with_results'], 1)

    def test_filters_heatmap_and_workflow(self):
        set_client_auth_cookies(self.client, self.admin)
        filters = self.client.get(self.filters_url)
        heatmap_missing = self.client.get(self.heatmap_url)
        heatmap = self.client.get(self.heatmap_url, {'level_id': str(self.level.id)})
        grade_missing = self.client.get(self.grade_url)
        grade = self.client.get(
            self.grade_url,
            {'class_level_id': str(self.class_level.id)},
        )
        workflow = self.client.get(self.workflow_url)

        self.assertEqual(filters.status_code, status.HTTP_200_OK)
        self.assertTrue(len(filters.data['terms']) >= 1)
        self.assertEqual(filters.data['levels'][0]['name'], 'JHS')

        self.assertEqual(heatmap_missing.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(heatmap.status_code, status.HTTP_200_OK)
        self.assertIn('Mathematics', heatmap.data['subjects'])
        self.assertEqual(heatmap.data['students_count'], 1)
        self.assertTrue(len(heatmap.data['class_sizes']) >= 1)
        self.assertEqual(heatmap.data['class_sizes'][0]['students_count'], 1)
        self.assertTrue(len(heatmap.data['cells']) >= 1)

        self.assertEqual(grade_missing.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(grade.status_code, status.HTTP_200_OK)
        self.assertEqual(grade.data['class_level_name'], 'JHS 1')
        self.assertEqual(grade.data['mode'], 'grades')

        self.assertEqual(workflow.status_code, status.HTTP_200_OK)
        self.assertIn('pending_count', workflow.data)

    def test_grade_distribution_score_bands_for_position_only(self):
        self.config.result_type = AssessmentConfig.ResultType.POSITION
        self.config.grade_type = None
        self.config.pass_mark = Decimal('40.00')
        self.config.save(
            update_fields=['result_type', 'grade_type', 'pass_mark', 'updated_at'],
        )
        self.config.grade_bands.all().delete()

        set_client_auth_cookies(self.client, self.admin)
        response = self.client.get(
            self.grade_url,
            {'class_level_id': str(self.class_level.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['mode'], 'score_bands')
        self.assertEqual(response.data['result_type'], 'position')
        self.assertEqual(response.data['pass_mark'], 40.0)
        self.assertGreater(response.data['total_graded'], 0)
        labels = [row['grade'] for row in response.data['results']]
        self.assertIn('Below 40', labels)
        self.assertTrue(any(row['count'] > 0 for row in response.data['results']))

    def test_teacher_desk_for_subject_teacher(self):
        set_client_auth_cookies(self.client, self.teacher)
        response = self.client.get(self.teacher_desk_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['scope_mode'], 'scoped')
        self.assertTrue(response.data['is_subject_teacher'])
        self.assertEqual(len(response.data['subjects']), 1)
        self.assertEqual(response.data['subjects'][0]['subject_name'], 'Mathematics')
        self.assertEqual(response.data['subjects'][0]['mode'], 'grades')
        self.assertEqual(response.data['subjects'][0]['students_count'], 1)
        self.assertGreater(response.data['subjects'][0]['score_count'], 0)
        self.assertEqual(len(response.data['subjects'][0]['students']), 1)

    def test_teacher_desk_subject_score_bands_for_position_only(self):
        self.config.result_type = AssessmentConfig.ResultType.POSITION
        self.config.grade_type = None
        self.config.pass_mark = Decimal('40.00')
        self.config.save(
            update_fields=['result_type', 'grade_type', 'pass_mark', 'updated_at'],
        )
        self.config.grade_bands.all().delete()

        set_client_auth_cookies(self.client, self.teacher)
        response = self.client.get(self.teacher_desk_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        subject = response.data['subjects'][0]
        self.assertEqual(subject['mode'], 'score_bands')
        self.assertEqual(subject['result_type'], 'position')
        self.assertGreater(subject['total_graded'], 0)
        labels = [row['grade'] for row in subject['grade_distribution']]
        self.assertIn('Below 40', labels)
        self.assertTrue(any(row['count'] > 0 for row in subject['grade_distribution']))

    def test_teacher_desk_for_class_teacher(self):
        ClassTeacher.objects.create(
            teacher=self.teacher,
            class_level=self.class_level,
            stream=self.stream,
            term=self.term,
        )
        set_client_auth_cookies(self.client, self.teacher)
        response = self.client.get(self.teacher_desk_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_class_teacher'])
        self.assertEqual(len(response.data['classes']), 1)
        self.assertEqual(response.data['classes'][0]['students_count'], 1)
        self.assertEqual(response.data['classes'][0]['students_with_results'], 1)

    def test_admin_teacher_desk_is_empty(self):
        set_client_auth_cookies(self.client, self.admin)
        response = self.client.get(self.teacher_desk_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['scope_mode'], 'school')
        self.assertEqual(response.data['classes'], [])
        self.assertEqual(response.data['subjects'], [])

    def test_staff_capacity_is_teacher_centric(self):
        ClassTeacher.objects.create(
            teacher=self.teacher,
            class_level=self.class_level,
            stream=self.stream,
            term=self.term,
        )
        set_client_auth_cookies(self.client, self.admin)
        response = self.client.get(self.staff_capacity_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['teachers_count'], 1)
        self.assertEqual(response.data['class_teachers_count'], 1)
        self.assertEqual(response.data['subject_teachers_count'], 1)
        self.assertEqual(response.data['both_roles_count'], 1)
        self.assertEqual(response.data['classes_without_class_teacher'], 0)
        self.assertEqual(len(response.data['results']), 1)
        teacher = response.data['results'][0]
        self.assertEqual(teacher['full_name'], 'Math Tutor')
        self.assertTrue(teacher['is_class_teacher'])
        self.assertTrue(teacher['is_subject_teacher'])
        self.assertEqual(teacher['class_teacher_count'], 1)
        self.assertEqual(teacher['class_teacher_students'], 1)
        self.assertEqual(teacher['subjects_taught_count'], 1)
        self.assertEqual(teacher['subject_names'], ['Mathematics'])
        self.assertEqual(teacher['teaching_assignments_count'], 1)
        self.assertEqual(teacher['classes_taught_count'], 1)

    def test_class_and_subject_performance_endpoints(self):
        class_url = reverse(
            'academics-class-performance',
            kwargs={'stream_id': self.stream.id},
        )
        subject_url = reverse(
            'academics-teaching-assignment-performance',
            kwargs={'assignment_id': self.assignment.id},
        )

        set_client_auth_cookies(self.client, self.admin)
        class_response = self.client.get(class_url)
        subject_response = self.client.get(subject_url)

        self.assertEqual(class_response.status_code, status.HTTP_200_OK)
        self.assertEqual(class_response.data['students_count'], 1)
        self.assertEqual(class_response.data['students_with_results'], 1)
        self.assertEqual(len(class_response.data['students']), 1)

        self.assertEqual(subject_response.status_code, status.HTTP_200_OK)
        self.assertEqual(subject_response.data['subject_name'], 'Mathematics')
        self.assertEqual(subject_response.data['students_count'], 1)
        self.assertEqual(subject_response.data['score_count'], 1)

        set_client_auth_cookies(self.client, self.teacher)
        teacher_subject = self.client.get(subject_url)
        self.assertEqual(teacher_subject.status_code, status.HTTP_200_OK)
        self.assertEqual(teacher_subject.data['score_count'], 1)

    def test_student_performance_across_terms(self):
        set_client_auth_cookies(self.client, self.admin)
        response = self.client.get(self.performance_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['student_id'], str(self.student.id))
        self.assertEqual(len(response.data['terms']), 1)
        self.assertEqual(len(response.data['overall_trend']), 1)
        term = response.data['terms'][0]
        self.assertEqual(term['subjects'][0]['subject_name'], 'Mathematics')
        self.assertEqual(term['subjects'][0]['rank'], 1)
        self.assertIn(term['subjects'][0]['rating'], {'strong', 'secure', 'borderline', 'at_risk'})
        self.assertIn(term['mode'], {'grades', 'score_bands'})
        self.assertGreater(len(response.data['subject_trends']), 0)
        self.assertEqual(len(response.data['all_time_ranking']), 1)
        self.assertEqual(response.data['all_time_ranking'][0]['rank'], 1)

    def test_enrollment_leaving_this_year_uses_final_class_name(self):
        jhs3 = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='JHS 3',
            order=3,
            is_system_generated=False,
        )
        jhs3_stream = ensure_default_stream(jhs3)
        leaver = create_student(
            school=self.school,
            first_name='Kojo',
            last_name='Mensah',
            student_id='SMS-LEAVE-1',
        )
        enroll_student(student=leaver, term=self.term, stream=jhs3_stream)

        set_client_auth_cookies(self.client, self.admin)
        response = self.client.get(reverse('reports-enrollment'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['leaving_this_year_class_name'], 'JHS 3')
        self.assertEqual(response.data['leaving_this_year_count'], 1)
        self.assertIsNone(response.data['graduated_count'])
        self.assertIsNone(response.data['graduated_class_name'])

    def test_enrollment_graduated_names_previous_class(self):
        previous_year = AcademicYear.objects.create(
            school=self.school,
            academic_year='2024/2025',
            start_date=date(2024, 9, 1),
            end_date=date(2025, 7, 31),
            is_active=False,
        )
        previous_term = Term.objects.create(
            school=self.school,
            academic_year=previous_year,
            term=Term.TermChoices.THIRD_TERM,
            start_date=date(2025, 4, 1),
            end_date=date(2025, 7, 31),
            is_active=False,
        )
        jhs3 = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='JHS 3',
            order=3,
            is_system_generated=False,
        )
        jhs3_stream = ensure_default_stream(jhs3)
        graduate = create_student(
            school=self.school,
            first_name='Ama',
            last_name='Serwaa',
            student_id='SMS-GRAD-1',
        )
        enroll_student(student=graduate, term=previous_term, stream=jhs3_stream)
        graduate.is_graduated = True
        graduate.save(update_fields=['is_graduated', 'updated_at'])

        set_client_auth_cookies(self.client, self.admin)
        response = self.client.get(
            reverse('reports-enrollment'),
            {'term_id': str(self.term.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['graduated_count'], 1)
        self.assertEqual(response.data['graduated_class_name'], 'JHS 3')
        self.assertEqual(response.data['leaving_this_year_class_name'], 'JHS 3')
