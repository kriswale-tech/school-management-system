import io
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.urls import reverse
from openpyxl import Workbook
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.models import User
from accounts.tests.factories import create_membership, create_user, set_client_auth_cookies, user_school
from fees.models import Payment, StudentFee
from migration.models import (
    FieldMapping,
    MappingProfile,
    MigrationAuditEvent,
    MigrationCommitRecord,
    MigrationFile,
    MigrationJob,
    MigrationRow,
)
from students.models import Student


def workbook_bytes(sheets):
    book = Workbook()
    first = True
    for name, rows in sheets:
        worksheet = book.active if first else book.create_sheet(name)
        worksheet.title = name
        first = False
        for row in rows:
            worksheet.append(row)
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


class MigrationPhase1Tests(APITestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        set_client_auth_cookies(self.client, self.user)
        self.school = user_school(self.user)
        self.students_before = Student.objects.count()
        self.fees_before = StudentFee.objects.count()
        self.payments_before = Payment.objects.count()

    def create_job(self, job_type='student_enrollment'):
        response = self.client.post(
            reverse('migration-job-list'),
            {'job_type': job_type, 'source_system': 'Legacy'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data['id']

    def upload(self, job_id, filename, content, content_type):
        return self.client.post(
            reverse('migration-job-upload', kwargs={'job_id': job_id}),
            {'file': SimpleUploadedFile(filename, content, content_type=content_type)},
            format='multipart',
        )

    def map_and_validate(self, job_id, sheet_id, mappings):
        saved = self.client.put(
            reverse('migration-sheet-mapping', kwargs={'job_id': job_id, 'sheet_id': sheet_id}),
            {'mappings': mappings},
            format='json',
        )
        self.assertEqual(saved.status_code, status.HTTP_200_OK, saved.data)
        validated = self.client.post(reverse('migration-job-validate', kwargs={'job_id': job_id}))
        self.assertEqual(validated.status_code, status.HTTP_200_OK, validated.data)
        return validated.data

    def assert_no_operational_writes(self):
        self.assertEqual(Student.objects.count(), self.students_before)
        self.assertEqual(StudentFee.objects.count(), self.fees_before)
        self.assertEqual(Payment.objects.count(), self.payments_before)
        self.assertEqual(MigrationCommitRecord.objects.count(), 0)

    def test_accountant_and_other_school_cannot_use_a_job(self):
        job_id = self.create_job()
        accountant = User.objects.create(
            phone_number='+233200000099',
            email='acct@test.com',
            first_name='Ama',
            last_name='Owusu',
            is_active=True,
        )
        accountant.set_unusable_password()
        accountant.save(update_fields=['password'])
        create_membership(accountant, self.school, role=User.RoleChoices.ACCOUNTANT)
        accountant_client = APIClient()
        set_client_auth_cookies(accountant_client, accountant, self.school)
        forbidden = accountant_client.get(reverse('migration-job-detail', kwargs={'job_id': job_id}))
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

        staff = User.objects.create(
            phone_number='+233200000077',
            email='staff-mig@test.com',
            first_name='Kojo',
            last_name='Mensah',
            is_active=True,
        )
        staff.set_unusable_password()
        staff.save(update_fields=['password'])
        create_membership(staff, self.school, role=User.RoleChoices.STAFF)
        staff_client = APIClient()
        set_client_auth_cookies(staff_client, staff, self.school)
        allowed = staff_client.get(reverse('migration-job-detail', kwargs={'job_id': job_id}))
        self.assertEqual(allowed.status_code, status.HTTP_200_OK, allowed.data)

        other = create_user(
            phone_number='+233244567891',
            email='other@test.com',
            is_active=True,
        )
        other_client = APIClient()
        set_client_auth_cookies(other_client, other)
        missing = other_client.get(reverse('migration-job-detail', kwargs={'job_id': job_id}))
        self.assertEqual(missing.status_code, status.HTTP_404_NOT_FOUND)
        self.assert_no_operational_writes()

    def test_xlsx_multiple_sheets_csv_and_rejected_files(self):
        job_id = self.create_job()
        content = workbook_bytes([
            ('Pupils', [
                ['Pupil Name', 'Sex', 'DOB', 'Admitted', 'Notes'],
                ['Ama Serwaa Mensah', 'F', '01/02/2020', '2020-09-01', 'keep me'],
                ['Kojo Mensah', 'M', '2019-05-04', '', 'missing date'],
            ]),
            ('Fees', [
                ['Student code', 'Balance'],
                ['STU-1', '20'],
            ]),
        ])
        uploaded = self.upload(
            job_id,
            'pupils.xlsx',
            content,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.assertEqual(uploaded.status_code, status.HTTP_201_CREATED, uploaded.data)
        self.assertEqual(uploaded.data['status'], 'ready')
        self.assertEqual(len(uploaded.data['file_hash']), 64)
        names = [sheet['sheet_name'] for sheet in uploaded.data['sheets']]
        self.assertEqual(names, ['Pupils', 'Fees'])
        pupils = next(sheet for sheet in uploaded.data['sheets'] if sheet['sheet_name'] == 'Pupils')
        self.assertEqual(pupils['detected_headers'][0], 'Pupil Name')
        self.assertEqual(pupils['row_count'], 2)
        self.assertIn('Ama Serwaa Mensah', pupils['sample_rows'][0].values())

        suggestions = self.client.get(reverse(
            'migration-sheet-suggest',
            kwargs={'job_id': job_id, 'sheet_id': pupils['id']},
        ))
        by_column = {item['source_column']: item for item in suggestions.data['suggestions']}
        self.assertEqual(by_column['Pupil Name']['target_field'], 'full_name')
        self.assertEqual(by_column['Pupil Name']['transforms'][0]['step'], 'split_name')
        self.assertEqual(by_column['DOB']['transforms'][0]['config']['format'], '%d/%m/%Y')
        self.assertTrue(by_column['Notes']['ignored'])

        self.map_and_validate(job_id, pupils['id'], [
            {
                'source_column': 'Pupil Name',
                'target_field': 'full_name',
                'transforms': [{'step': 'split_name', 'config': {}}],
            },
            {
                'source_column': 'Sex',
                'target_field': 'gender',
                'transforms': [{'step': 'value_map', 'config': {'map': {'F': 'female', 'M': 'male'}}}],
            },
            {
                'source_column': 'DOB',
                'target_field': 'date_of_birth',
                'transforms': [{'step': 'date', 'config': {'format': '%d/%m/%Y'}}],
            },
            {
                'source_column': 'Admitted',
                'target_field': 'admission_date',
                'transforms': [{'step': 'date', 'config': {'format': '%Y-%m-%d'}}],
            },
            {'source_column': 'Notes', 'target_field': '', 'ignored': True},
        ])
        preview = self.client.get(reverse('migration-job-preview', kwargs={'job_id': job_id}))
        rows = {row['source_row_number']: row for row in preview.data['rows'] if row['sheet_name'] == 'Pupils'}
        ready = rows[2]
        blocked = rows[3]
        self.assertEqual(ready['validation_status'], 'ready')
        self.assertEqual(ready['raw_values']['Pupil Name'], 'Ama Serwaa Mensah')
        self.assertEqual(ready['transformed_values']['first_name'], 'Ama')
        self.assertEqual(ready['transformed_values']['other_names'], 'Serwaa')
        self.assertEqual(ready['transformed_values']['last_name'], 'Mensah')
        self.assertEqual(ready['transformed_values']['date_of_birth'], '2020-02-01')
        self.assertEqual(ready['transformed_values']['gender'], 'female')
        self.assertEqual(blocked['validation_status'], 'blocked')
        self.assertEqual(preview.data['summary']['ready_rows'], 1)
        self.assertGreaterEqual(preview.data['summary']['blocked_rows'], 1)
        self.assertTrue(any(item['column'] == 'Notes' for item in preview.data['summary']['unmapped_columns']))

        self.map_and_validate(job_id, pupils['id'], [
            {
                'source_column': 'Pupil Name',
                'target_field': 'full_name',
                'transforms': [{'step': 'split_name', 'config': {}}],
            },
            {
                'source_column': 'Sex',
                'target_field': 'gender',
                'transforms': [{'step': 'value_map', 'config': {'map': {'F': 'female', 'M': 'male'}}}],
            },
            {
                'source_column': 'DOB',
                'target_field': 'date_of_birth',
                'transforms': [{'step': 'date', 'config': {}}],
            },
            {
                'source_column': 'Admitted',
                'target_field': 'admission_date',
                'transforms': [{'step': 'date', 'config': {'format': '%Y-%m-%d'}}],
            },
        ])
        preview = self.client.get(reverse('migration-job-preview', kwargs={'job_id': job_id}))
        rows = {row['source_row_number']: row for row in preview.data['rows'] if row['sheet_name'] == 'Pupils'}
        self.assertEqual(rows[2]['validation_status'], 'blocked')
        self.assertEqual(rows[2]['raw_values']['DOB'], '01/02/2020')
        self.assertIn('not guessed', rows[2]['errors'][0]['message'])
        self.assertEqual(rows[3]['raw_values']['DOB'], '2019-05-04')

        duplicate = self.upload(
            job_id,
            'pupils-again.xlsx',
            content,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.assertEqual(duplicate.status_code, status.HTTP_201_CREATED, duplicate.data)
        replaced = self.client.get(reverse('migration-job-detail', kwargs={'job_id': job_id}))
        self.assertEqual([item['original_filename'] for item in replaced.data['files']], ['pupils-again.xlsx'])

        semicolon = self.upload(
            job_id,
            'semicolon.csv',
            'Pupil Name;Sex\nYaw Owusu;M\n'.encode(),
            'text/csv',
        )
        self.assertEqual(semicolon.status_code, status.HTTP_201_CREATED, semicolon.data)
        self.assertEqual(semicolon.data['detected_delimiter'], ';')
        self.assertEqual(semicolon.data['detected_encoding'], 'utf-8')

        tabbed = self.upload(
            job_id,
            'tab.csv',
            'Pupil Name\tSex\nEsi Amponsah\tF\n'.encode('utf-8-sig'),
            'text/csv',
        )
        self.assertEqual(tabbed.data['detected_delimiter'], '\t')
        self.assertEqual(tabbed.data['detected_encoding'], 'utf-8-sig')

        windows = self.upload(
            job_id,
            'windows.csv',
            'Pupil Name,Sex\nJoël Mensah,M\n'.encode('cp1252'),
            'text/csv',
        )
        self.assertEqual(windows.data['detected_encoding'], 'cp1252')
        self.assertEqual(windows.data['sheets'][0]['sample_rows'][0]['Pupil Name'], 'Joël Mensah')

        broken = self.upload(job_id, 'broken.xlsx', b'this is not a workbook', 'application/octet-stream')
        self.assertEqual(broken.status_code, status.HTTP_201_CREATED)
        self.assertEqual(broken.data['status'], 'rejected')
        self.assertIn('could not be opened', broken.data['error'])

        old = self.upload(job_id, 'legacy.xls', b'old', 'application/vnd.ms-excel')
        self.assertEqual(old.status_code, status.HTTP_400_BAD_REQUEST)
        self.assert_no_operational_writes()

    def test_profiles_phone_trim_combine_and_duplicates(self):
        job_id = self.create_job()
        content = (
            'First,Last,Sex,DOB,Admitted,Phone,Student ID\n'
            ' Ama ,Mensah,female,2020-01-02,2020-09-01,0244111222,STU-9\n'
            'Kofi,Asare,female,2020-01-02,2020-09-01,not-a-phone,STU-9\n'
        ).encode()
        uploaded = self.upload(job_id, 'pupils.csv', content, 'text/csv')
        sheet_id = uploaded.data['sheets'][0]['id']
        mappings = [
            {'source_column': 'First', 'target_field': 'first_name', 'transforms': [{'step': 'trim', 'config': {}}]},
            {'source_column': 'Last', 'target_field': 'last_name', 'transforms': [{'step': 'trim', 'config': {}}]},
            {'source_column': 'Sex', 'target_field': 'gender'},
            {'source_column': 'DOB', 'target_field': 'date_of_birth', 'transforms': [{'step': 'date', 'config': {'format': '%Y-%m-%d'}}]},
            {'source_column': 'Admitted', 'target_field': 'admission_date', 'transforms': [{'step': 'date', 'config': {'format': '%Y-%m-%d'}}]},
            {'source_column': 'Phone', 'target_field': 'guardian_phone', 'transforms': [{'step': 'phone', 'config': {}}]},
            {'source_column': 'Student ID', 'target_field': 'student_id', 'transforms': [{'step': 'trim', 'config': {}}]},
            {
                'source_column': 'First',
                'target_field': 'full_name',
                'transforms': [{'step': 'combine', 'config': {'columns': ['First', 'Last'], 'separator': ' '}}],
            },
        ]
        summary = self.map_and_validate(job_id, sheet_id, mappings)
        self.assertEqual(summary['ready_rows'], 0)
        self.assertEqual(summary['blocked_rows'], 2)
        preview = self.client.get(reverse('migration-job-preview', kwargs={'job_id': job_id}))
        first = preview.data['rows'][0]
        second = preview.data['rows'][1]
        self.assertEqual(first['raw_values']['First'], ' Ama ')
        self.assertEqual(first['transformed_values']['first_name'], 'Ama')
        self.assertEqual(first['transformed_values']['full_name'], 'Ama Mensah')
        self.assertEqual(first['transformed_values']['guardian_phone'], '+233244111222')
        self.assertEqual(second['validation_status'], 'blocked')
        self.assertTrue(any('more than once' in item['message'] for item in second['errors']))
        self.assertTrue(any('phone' in warning['message'].lower() or 'Invalid phone' in warning['message'] for warning in second['warnings']))
        self.assertTrue(any('STU-9' in warning['message'] for warning in first['warnings']))

        saved = self.client.post(
            reverse('migration-profile-create', kwargs={'job_id': job_id, 'sheet_id': sheet_id}),
            {'name': 'Legacy pupils', 'source_system': 'Legacy', 'mappings': mappings},
            format='json',
        )
        self.assertEqual(saved.status_code, status.HTTP_201_CREATED)
        profiles = self.client.get(reverse('migration-profile-list') + '?job_type=student_enrollment')
        self.assertEqual(profiles.data[0]['name'], 'Legacy pupils')

        fee_job = self.create_job('fee_financial_history')
        fee_upload = self.upload(fee_job, 'fees.csv', b'Student ID,Amount\nSTU-9,10\n', 'text/csv')
        fee_sheet = fee_upload.data['sheets'][0]['id']
        wrong_profile = self.client.post(
            reverse('migration-profile-apply', kwargs={'job_id': fee_job, 'sheet_id': fee_sheet}),
            {'profile_id': saved.data['id']},
            format='json',
        )
        self.assertEqual(wrong_profile.status_code, status.HTTP_404_NOT_FOUND)

        second_job = self.create_job()
        second_upload = self.upload(second_job, 'again.csv', content, 'text/csv')
        applied = self.client.post(
            reverse('migration-profile-apply', kwargs={'job_id': second_job, 'sheet_id': second_upload.data['sheets'][0]['id']}),
            {'profile_id': saved.data['id']},
            format='json',
        )
        self.assertEqual(applied.status_code, status.HTTP_200_OK)
        mapped = applied.data['files'][0]['sheets'][0]['mappings']
        self.assertTrue(any(item['target_field'] == 'first_name' for item in mapped))
        download = self.client.get(reverse(
            'migration-file-download',
            kwargs={'job_id': job_id, 'file_id': uploaded.data['id']},
        ))
        self.assertEqual(download.status_code, status.HTTP_200_OK)
        self.assertIn(b'Ama', b''.join(download.streaming_content))
        self.assertTrue(MigrationAuditEvent.objects.filter(job_id=job_id, action='download').exists())
        self.assert_no_operational_writes()

    def test_model_constraints_are_school_scoped(self):
        other = create_user(phone_number='+233244567892', email='school2@test.com', is_active=True)
        other_school = user_school(other)
        MappingProfile.objects.create(
            school=self.school,
            name='Shared label',
            job_type=MigrationJob.JobType.STUDENT_ENROLLMENT,
            created_by=self.user,
        )
        MappingProfile.objects.create(
            school=other_school,
            name='Shared label',
            job_type=MigrationJob.JobType.STUDENT_ENROLLMENT,
            created_by=other,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MappingProfile.objects.create(
                    school=self.school,
                    name='Shared label',
                    job_type=MigrationJob.JobType.STUDENT_ENROLLMENT,
                    created_by=self.user,
                )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                FieldMapping.objects.create(source_column='Name')

        job = MigrationJob.objects.create(
            school=self.school,
            job_type=MigrationJob.JobType.FEE_FINANCIAL_HISTORY,
            created_by=self.user,
        )
        MigrationCommitRecord.objects.create(
            school=self.school,
            job_type=job.job_type,
            file_hash='a' * 64,
            sheet_name='Fees',
            source_row_number=2,
            job=job,
            source_transaction_id='SRC-1',
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MigrationCommitRecord.objects.create(
                    school=self.school,
                    job_type=job.job_type,
                    file_hash='a' * 64,
                    sheet_name='Fees',
                    source_row_number=2,
                    job=job,
                )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MigrationCommitRecord.objects.create(
                    school=self.school,
                    job_type=job.job_type,
                    file_hash='b' * 64,
                    sheet_name='Fees',
                    source_row_number=3,
                    source_transaction_id='SRC-1',
                )
        MigrationCommitRecord.objects.create(
            school=other_school,
            job_type=job.job_type,
            file_hash='a' * 64,
            sheet_name='Fees',
            source_row_number=2,
            source_transaction_id='SRC-1',
        )
        self.assertEqual(Student.objects.count(), self.students_before)

    def test_header_row_can_be_changed(self):
        job_id = self.create_job()
        content = workbook_bytes([
            ('Pupils', [
                ['Exported from legacy'],
                ['Pupil Name', 'Sex', 'DOB', 'Admitted'],
                ['Ama Mensah', 'F', date(2020, 2, 1), date(2020, 9, 1)],
            ]),
        ])
        uploaded = self.upload(job_id, 'banner.xlsx', content, 'application/octet-stream')
        sheet = uploaded.data['sheets'][0]
        self.assertEqual(sheet['header_row'], 1)
        changed = self.client.post(
            reverse('migration-sheet-header', kwargs={'job_id': job_id, 'sheet_id': sheet['id']}),
            {'header_row': 2},
            format='json',
        )
        self.assertEqual(changed.status_code, status.HTTP_200_OK, changed.data)
        updated = changed.data['files'][0]['sheets'][0]
        self.assertEqual(updated['detected_headers'][0], 'Pupil Name')
        self.assertEqual(updated['row_count'], 1)
        self.assertEqual(MigrationRow.objects.filter(sheet_id=sheet['id']).count(), 1)
        self.assert_no_operational_writes()

    def test_named_month_dates_are_read(self):
        job_id = self.create_job()
        content = (
            'First,Last,Sex,DOB,Admitted\n'
            'Ama,Mensah,female,17 Nov 2026,17th November 2026\n'
            'Kojo,Asare,male,"November 17, 2026",17th of November 2026\n'
            'Esi,Owusu,female,01/02/2026,32 November 2026\n'
        ).encode()
        uploaded = self.upload(job_id, 'dates.csv', content, 'text/csv')
        sheet_id = uploaded.data['sheets'][0]['id']
        self.map_and_validate(job_id, sheet_id, [
            {'source_column': 'First', 'target_field': 'first_name', 'transforms': [{'step': 'trim', 'config': {}}]},
            {'source_column': 'Last', 'target_field': 'last_name', 'transforms': [{'step': 'trim', 'config': {}}]},
            {'source_column': 'Sex', 'target_field': 'gender', 'transforms': [{'step': 'trim', 'config': {}}]},
            {'source_column': 'DOB', 'target_field': 'date_of_birth', 'transforms': [{'step': 'date', 'config': {'format': '%d/%m/%Y'}}]},
            {'source_column': 'Admitted', 'target_field': 'admission_date', 'transforms': [{'step': 'date', 'config': {'format': '%d/%m/%Y'}}]},
        ])
        preview = self.client.get(reverse('migration-job-preview', kwargs={'job_id': job_id}))
        rows = {row['raw_values']['First']: row for row in preview.data['rows']}
        self.assertEqual(rows['Ama']['transformed_values']['date_of_birth'], '2026-11-17')
        self.assertEqual(rows['Ama']['transformed_values']['admission_date'], '2026-11-17')
        self.assertEqual(rows['Ama']['raw_values']['DOB'], '17 Nov 2026')
        self.assertEqual(rows['Kojo']['transformed_values']['date_of_birth'], '2026-11-17')
        self.assertEqual(rows['Kojo']['transformed_values']['admission_date'], '2026-11-17')
        self.assertEqual(rows['Esi']['transformed_values']['date_of_birth'], '2026-02-01')
        self.assertEqual(rows['Esi']['validation_status'], 'blocked')
        self.assertIn('32 November 2026', rows['Esi']['errors'][0]['message'])
