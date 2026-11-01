from datetime import date
from unittest.mock import patch

from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, Level
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from assessments.models import Report, StudentResult
from assessments.services.report_links import build_report_public_url, make_report_token
from assessments.services.report_ready_notices import maybe_auto_notify_report_ready
from notifications.models import GuardianDelivery
from schools.models import AcademicYear, SchoolSettings, Term
from schools.services.settings import get_school_settings
from students.models import Parent, StudentParent
from students.tests.factories import create_student, enroll_student, ensure_default_stream

SEND_SMS_PATH = 'shared.services.arkesel_sms.send_sms_to_recipients'
FILE_EXISTS_PATH = 'assessments.services.report_ready_notices._report_file_exists'
SIGNED_URL_PATH = 'assessments.public_views._signed_url'


class ReportReadyNoticeAPITests(APITestCase):
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
        class_level = ClassLevel.objects.create(
            school=self.school,
            level=level,
            name='JHS 1',
            is_system_generated=False,
        )
        self.stream = ensure_default_stream(class_level)

        self.with_report = create_student(
            school=self.school,
            student_id='RR-0001',
            first_name='Ama',
            last_name='Mensah',
        )
        self.no_report = create_student(
            school=self.school,
            student_id='RR-0002',
            first_name='Kojo',
            last_name='Boateng',
        )
        for student in (self.with_report, self.no_report):
            enroll_student(
                student=student,
                term=self.term,
                stream=self.stream,
                is_new_student=True,
            )
            parent = Parent.objects.create(
                school=self.school,
                name=f'Parent {student.first_name}',
                phone_number=f'+23324400{student.student_id[-4:]}01',
                email=f'{student.student_id.lower()}@example.com',
                notify_channel=Parent.NotifyChannel.BOTH,
            )
            StudentParent.objects.create(
                student=student,
                parent=parent,
                relationship=StudentParent.RelationshipChoices.FATHER,
                is_primary=True,
            )
            StudentResult.objects.create(
                student=student,
                term=self.term,
                class_level=class_level,
                stream=self.stream,
                status=StudentResult.Status.RELEASED,
            )

        self.report = Report.objects.create(
            school=self.school,
            student=self.with_report,
            stream=self.stream,
            term=self.term,
            file='reports/test/ama_mensah.pdf',
            generated_at=timezone.now(),
            generated_by=self.user,
        )

        settings_row = get_school_settings(self.school)
        settings_row.guardian_report_ready_enabled = True
        settings_row.guardian_report_ready_channels = SchoolSettings.GuardianChannel.BOTH
        settings_row.report_parent_notify_mode = SchoolSettings.ReportParentNotifyMode.MANUAL
        settings_row.save()

        self.preview_url = reverse(
            'academics-assessments-admin-report-ready-preview',
            kwargs={'stream_id': self.stream.id},
        )
        self.send_url = reverse(
            'academics-assessments-admin-report-ready-send',
            kwargs={'stream_id': self.stream.id},
        )

    @patch(FILE_EXISTS_PATH, return_value=True)
    def test_preview_counts_only_students_with_reports(self, _mock_exists):
        response = self.client.post(
            self.preview_url,
            {
                'term_id': str(self.term.id),
                'student_ids': [str(self.with_report.id), str(self.no_report.id)],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['enabled'])
        self.assertEqual(response.data['eligible_count'], 1)
        self.assertEqual(response.data['skipped_count'], 1)
        self.assertEqual(response.data['sms_count'], 1)
        self.assertEqual(response.data['email_count'], 1)
        self.assertEqual(response.data['eligible_ids'], [str(self.with_report.id)])
        self.assertEqual(response.data['notify_mode'], 'manual')

    @patch(FILE_EXISTS_PATH, return_value=True)
    def test_preview_when_disabled(self, _mock_exists):
        settings_row = get_school_settings(self.school)
        settings_row.guardian_report_ready_enabled = False
        settings_row.save(update_fields=['guardian_report_ready_enabled', 'updated_at'])

        response = self.client.post(
            self.preview_url,
            {
                'term_id': str(self.term.id),
                'student_ids': [str(self.with_report.id)],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['enabled'])
        self.assertEqual(response.data['sms_count'], 0)

    @patch(FILE_EXISTS_PATH, return_value=True)
    @patch(SEND_SMS_PATH, return_value={'status': 'success', 'data': [{'id': 'rr-1'}]})
    def test_send_creates_deliveries(self, mock_sms, _mock_exists):
        response = self.client.post(
            self.send_url,
            {
                'term_id': str(self.term.id),
                'student_ids': [str(self.with_report.id), str(self.no_report.id)],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['queued'])
        self.assertEqual(response.data['students_notified'], 1)
        self.assertEqual(response.data['sms_sent'], 1)
        self.assertEqual(response.data['email_sent'], 1)
        mock_sms.assert_called_once()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('report', mail.outbox[0].body.lower())
        self.assertEqual(
            GuardianDelivery.objects.filter(
                event_type=GuardianDelivery.EventType.REPORT_READY,
                status=GuardianDelivery.Status.SENT,
            ).count(),
            2,
        )

    @patch(FILE_EXISTS_PATH, return_value=True)
    def test_send_rejects_when_disabled(self, _mock_exists):
        settings_row = get_school_settings(self.school)
        settings_row.guardian_report_ready_enabled = False
        settings_row.save(update_fields=['guardian_report_ready_enabled', 'updated_at'])

        response = self.client.post(
            self.send_url,
            {
                'term_id': str(self.term.id),
                'student_ids': [str(self.with_report.id)],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(FILE_EXISTS_PATH, return_value=True)
    def test_send_rejects_empty_eligible(self, _mock_exists):
        response = self.client.post(
            self.send_url,
            {
                'term_id': str(self.term.id),
                'student_ids': [str(self.no_report.id)],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(FILE_EXISTS_PATH, return_value=True)
    @patch(SEND_SMS_PATH, return_value={'status': 'success', 'data': [{'id': 'rr-auto'}]})
    def test_auto_notify_respects_mode(self, mock_sms, _mock_exists):
        settings_row = get_school_settings(self.school)
        settings_row.report_parent_notify_mode = SchoolSettings.ReportParentNotifyMode.MANUAL
        settings_row.save(update_fields=['report_parent_notify_mode', 'updated_at'])

        maybe_auto_notify_report_ready(report=self.report)
        mock_sms.assert_not_called()
        self.assertEqual(len(mail.outbox), 0)

        settings_row.report_parent_notify_mode = SchoolSettings.ReportParentNotifyMode.AUTO
        settings_row.save(update_fields=['report_parent_notify_mode', 'updated_at'])

        maybe_auto_notify_report_ready(report=self.report)
        mock_sms.assert_called_once()
        self.assertEqual(len(mail.outbox), 1)

    def test_public_report_bad_token(self):
        url = reverse('public-report', kwargs={'token': 'not-a-valid-token'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(SIGNED_URL_PATH, return_value='https://files.example/report.pdf')
    @patch(
        'assessments.services.report_links._report_file_exists',
        return_value=True,
    )
    def test_public_report_redirects(self, _mock_exists, _mock_signed):
        token = make_report_token(self.report.id)
        url = reverse('public-report', kwargs={'token': token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response['Location'], 'https://files.example/report.pdf')
        self.assertIn('/api/v1/public/reports/', build_report_public_url(self.report.id))
