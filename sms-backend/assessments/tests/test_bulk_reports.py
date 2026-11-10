from datetime import date
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, Level
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from assessments.models import Report, ReportGenerateJob, StudentResult
from assessments.services.bulk_reports import process_report_generate_job
from schools.models import AcademicYear, Term
from students.tests.factories import create_student, enroll_student, ensure_default_stream

GENERATE_PATH = 'assessments.services.bulk_reports.generate_student_report'
FILE_EXISTS_PATH = 'assessments.services.report_pdf._report_file_exists'


class BulkReportGenerateAPITests(APITestCase):
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
        level = Level.objects.create(
            school=self.school,
            name='Junior High',
            is_system_generated=False,
        )
        self.class_level = ClassLevel.objects.create(
            school=self.school,
            level=level,
            name='JHS 1',
            is_system_generated=False,
        )
        self.stream = ensure_default_stream(self.class_level)
        self.student = create_student(
            school=self.school,
            student_id='BG-0001',
            first_name='Ama',
            last_name='Mensah',
        )
        enroll_student(
            student=self.student,
            term=self.term,
            stream=self.stream,
            is_new_student=True,
        )
        StudentResult.objects.create(
            student=self.student,
            term=self.term,
            class_level=self.class_level,
            stream=self.stream,
            status=StudentResult.Status.RELEASED,
        )
        self.queue_url = reverse(
            'academics-assessments-admin-reports-generate',
            kwargs={'stream_id': self.stream.id},
        )

    @patch('assessments.tasks.run_report_generate_job_task.delay')
    def test_queue_bulk_generate_creates_job(self, mock_delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                self.queue_url,
                {
                    'term_id': str(self.term.id),
                    'student_ids': [str(self.student.id)],
                },
                format='json',
            )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['total'], 1)
        self.assertTrue(
            ReportGenerateJob.objects.filter(id=response.data['id']).exists(),
        )
        mock_delay.assert_called_once_with(str(response.data['id']))

        job_url = reverse(
            'academics-assessments-admin-reports-generate-job',
            kwargs={'stream_id': self.stream.id, 'job_id': response.data['id']},
        )
        status_response = self.client.get(job_url)
        self.assertEqual(status_response.status_code, status.HTTP_200_OK)
        self.assertEqual(status_response.data['id'], response.data['id'])

    @patch(FILE_EXISTS_PATH, return_value=True)
    @patch(GENERATE_PATH)
    def test_process_skips_existing_file(self, mock_generate, _mock_exists):
        mock_generate.return_value = {
            'id': 'report-id',
            'student_id': str(self.student.id),
            'stream_id': str(self.stream.id),
            'term_id': str(self.term.id),
            'generated_at': timezone.now().isoformat(),
            'url': 'https://example.com/r.pdf',
            'url_expires_in': 3600,
            'status': 'ready',
        }
        Report.objects.create(
            school=self.school,
            student=self.student,
            stream=self.stream,
            term=self.term,
            file='reports/test/existing.pdf',
            generated_at=timezone.now(),
        )
        job = ReportGenerateJob.objects.create(
            school=self.school,
            stream=self.stream,
            term=self.term,
            created_by=self.user,
            student_ids=[str(self.student.id)],
            total=1,
            force=False,
        )
        result = process_report_generate_job(job_id=str(job.id))
        job.refresh_from_db()
        self.assertEqual(job.status, ReportGenerateJob.Status.COMPLETED)
        self.assertEqual(result['skipped'], 1)
        self.assertEqual(result['generated'], 0)
        mock_generate.assert_called_once()
        self.assertFalse(mock_generate.call_args.kwargs.get('force'))
