from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import load_workbook
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from academics.models import ClassLevel, ClassStream, Level
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from fees.models import StudentFee
from migration.models import MigrationAuditEvent, MigrationJob, MigrationRow, SchoolValueMapping
from schools.models import AcademicYear, Term
from students.models import Student
from students.tests.factories import create_student, ensure_default_stream


class TemplateMigrationTests(APITestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        set_client_auth_cookies(self.client, self.user)
        self.school = user_school(self.user)
        self.year = AcademicYear.objects.create(
            school=self.school,
            academic_year='2025/2026',
            start_date='2025-09-01',
            end_date='2026-07-31',
            is_active=True,
        )
        self.term = Term.objects.create(
            school=self.school,
            academic_year=self.year,
            term=Term.TermChoices.FIRST_TERM,
            start_date='2025-09-01',
            end_date='2025-12-15',
            is_active=True,
        )
        self.level = Level.objects.create(school=self.school, name='Junior High', is_system_generated=False)
        self.class_level = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='JHS 1',
            is_system_generated=False,
        )
        self.stream = ensure_default_stream(self.class_level)
        self.stream_a = ClassStream.objects.create(class_level=self.class_level, name='A', is_default=False)

    def upload(self, template, content, filename='pupils.csv'):
        created = self.client.post(
            reverse('migration-job-list'),
            {'job_type': 'student_enrollment', 'template': template, 'source_system': 'Legacy'},
            format='json',
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        job_id = created.data['id']
        uploaded = self.client.post(
            reverse('migration-job-upload', kwargs={'job_id': job_id}),
            {'file': SimpleUploadedFile(filename, content.encode(), content_type='text/csv')},
            format='multipart',
        )
        self.assertEqual(uploaded.status_code, status.HTTP_201_CREATED, uploaded.data)
        sheet_id = uploaded.data['sheets'][0]['id']
        suggestions = self.client.get(reverse(
            'migration-sheet-suggest',
            kwargs={'job_id': job_id, 'sheet_id': sheet_id},
        ))
        self.assertEqual(suggestions.status_code, status.HTTP_200_OK, suggestions.data)
        saved = self.client.put(
            reverse('migration-sheet-mapping', kwargs={'job_id': job_id, 'sheet_id': sheet_id}),
            {'mappings': suggestions.data['suggestions']},
            format='json',
        )
        self.assertEqual(saved.status_code, status.HTTP_200_OK, saved.data)
        validated = self.client.post(reverse('migration-job-validate', kwargs={'job_id': job_id}))
        self.assertEqual(validated.status_code, status.HTTP_200_OK, validated.data)
        return job_id, suggestions.data

    def preview(self, job_id):
        response = self.client.get(reverse('migration-job-preview', kwargs={'job_id': job_id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data

    def test_template_download_includes_fields_and_notes(self):
        response = self.client.get(reverse('migration-template', kwargs={'template': 'student_information'}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        workbook = load_workbook(BytesIO(response.content))
        headers = [cell.value for cell in workbook['Students'][1]]
        self.assertEqual(headers, [
            'Student ID', 'First name', 'Last name', 'Other names', 'Gender', 'Date of birth',
            'Admission date', 'New student', 'Class', 'Stream', 'Guardian name', 'Guardian phone',
            'Guardian email', 'Relationship', 'Status',
        ])
        self.assertIn('One row is one student.', [row[0].value for row in workbook['Notes'].iter_rows()])

    def test_flexible_headers_split_a_full_name_and_require_gender_approval(self):
        job_id, suggestions = self.upload(
            'student_information',
            'Pupil Name,Sex,Birthday,Date Joined,Current Class,Parent Contact\n'
            'Ama Mensah,F,15/01/2010,01/09/2025,JHS 1 A,0244000001\n',
        )
        mapped = {item['source_column']: item['target_field'] for item in suggestions['suggestions']}
        self.assertEqual(mapped['Pupil Name'], 'full_name')
        self.assertEqual(mapped['Sex'], 'gender')
        self.assertEqual(mapped['Current Class'], 'class_name')
        self.assertEqual(mapped['Parent Contact'], 'guardian_phone')
        self.assertTrue(suggestions['unmapped_required'] == [])
        preview = self.preview(job_id)
        row = preview['rows'][0]
        self.assertEqual(row['transformed_values']['first_name'], 'Ama')
        self.assertEqual(row['transformed_values']['last_name'], 'Mensah')
        self.assertEqual(row['raw_values']['Sex'], 'F')
        self.assertTrue(row['proposal']['blocked'])
        values = self.client.get(reverse('migration-value-reconciliation', kwargs={'job_id': job_id}))
        gender = next(item for item in values.data['fields'] if item['field'] == 'gender')
        self.assertEqual(gender['values'][0]['label'], 'F')
        self.assertEqual(gender['values'][0]['status'], 'suggested')
        self.assertEqual(gender['values'][0]['count'], 1)
        approved = self.client.post(
            reverse('migration-value-reconciliation', kwargs={'job_id': job_id}),
            {'values': [{
                'field': 'gender',
                'source_value': gender['values'][0]['source_value'],
                'label': 'F',
                'canonical_value': 'female',
            }]},
            format='json',
        )
        self.assertEqual(approved.status_code, status.HTTP_200_OK, approved.data)
        preview = self.preview(job_id)
        self.assertEqual(preview['rows'][0]['transformed_values']['gender'], 'female')
        self.assertEqual(preview['rows'][0]['raw_values']['Sex'], 'F')
        self.assertFalse(preview['rows'][0]['proposal']['blocked'])
        self.assertEqual(preview['rows'][0]['proposal']['enrollment']['action'], 'current')
        self.assertTrue(MigrationAuditEvent.objects.filter(job_id=job_id, action='mapping').exists())
        self.client.post(reverse('migration-job-commit', kwargs={'job_id': job_id}), {'confirm': True}, format='json')
        student = Student.objects.get(first_name='Ama')
        self.assertEqual(student.gender, 'female')
        self.assertEqual(student.enrollments.get().stream_id, self.stream_a.id)
        self.assertEqual(StudentFee.objects.count(), 0)
        self.assertEqual(AcademicYear.objects.filter(school=self.school).count(), 1)

    def test_missing_required_column_blocks_and_optional_column_does_not(self):
        job_id, suggestions = self.upload(
            'student_information',
            'First name,Last name,Date of birth,Admission date\n'
            'Ama,Mensah,2010-01-15,2025-09-01\n',
        )
        self.assertIn('gender', [item['key'] for item in suggestions['unmapped_required']])
        preview = self.preview(job_id)
        self.assertEqual(preview['rows'][0]['validation_status'], 'blocked')
        other = self.upload(
            'student_information',
            'First name,Last name,Gender,Date of birth,Admission date\n'
            'Kojo,Mensah,male,2011-01-01,2025-09-01\n',
        )
        ready = self.preview(other[0])
        self.assertEqual(ready['rows'][0]['validation_status'], 'ready')

    def test_exact_class_separate_stream_and_inferred_combined_class(self):
        exact_id, _suggestions = self.upload(
            'student_information',
            'First name,Last name,Gender,Date of birth,Admission date,Class,Stream\n'
            'Kojo,Mensah,male,2011-01-01,2025-09-01,JHS 1,A\n',
        )
        exact = self.preview(exact_id)['rows'][0]
        self.assertEqual(exact['proposal']['enrollment']['action'], 'current')
        self.assertEqual(exact['proposal']['enrollment']['stream_id'], str(self.stream_a.id))

        job_id, _suggestions = self.upload(
            'student_information',
            'First name,Last name,Gender,Date of birth,Admission date,Class\n'
            'Ama,Mensah,female,2010-01-15,2025-09-01,JHS 1A\n'
            'Esi,Mensah,female,2012-01-01,2025-09-01,JHS 1A\n'
            'Yaw,Mensah,male,2013-01-01,2025-09-01,Form 9\n',
        )
        classes = self.client.get(reverse('migration-class-resolution', kwargs={'job_id': job_id}))
        by_label = {item['label']: item for item in classes.data['classes']}
        self.assertEqual(by_label['JHS 1A']['status'], 'inferred')
        self.assertEqual(by_label['JHS 1A']['count'], 2)
        self.assertEqual(by_label['JHS 1A']['stream_id'], str(self.stream_a.id))
        self.assertEqual(by_label['Form 9']['status'], 'unresolved')
        confirmed = self.client.post(
            reverse('migration-class-resolution', kwargs={'job_id': job_id}),
            {'source_value': by_label['JHS 1A']['source_value'], 'stream_id': self.stream_a.id},
            format='json',
        )
        self.assertEqual(confirmed.status_code, status.HTTP_200_OK, confirmed.data)
        self.assertEqual(confirmed.data['classes'][0]['status'] if False else next(
            item['status'] for item in confirmed.data['classes'] if item['label'] == 'JHS 1A'
        ), 'confirmed')
        preview = {row['transformed_values']['first_name']: row for row in self.preview(job_id)['rows']}
        self.assertFalse(preview['Ama']['proposal']['blocked'])
        self.assertFalse(preview['Esi']['proposal']['blocked'])
        self.assertTrue(preview['Yaw']['proposal']['blocked'])
        self.assertFalse(ClassLevel.objects.filter(school=self.school, name='Form 9').exists())

    def test_manual_class_alias_is_school_specific(self):
        basic_level = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='Basic 1',
            is_system_generated=False,
        )
        basic = ensure_default_stream(basic_level)
        job_id, _suggestions = self.upload(
            'student_information',
            'First name,Last name,Gender,Date of birth,Admission date,Class\n'
            'Ama,Mensah,female,2010-01-15,2025-09-01,Primary 1\n',
        )
        classes = self.client.get(reverse('migration-class-resolution', kwargs={'job_id': job_id})).data['classes']
        self.assertEqual(classes[0]['status'], 'unresolved')
        self.client.post(
            reverse('migration-class-resolution', kwargs={'job_id': job_id}),
            {'source_value': classes[0]['source_value'], 'stream_id': str(basic.id)},
            format='json',
        )
        self.assertTrue(SchoolValueMapping.objects.filter(school=self.school, field_name='class_name', source_value='primary 1').exists())

        other = create_user(phone_number='+233244567899', email='other-school@test.com', is_active=True)
        other_school = user_school(other)
        other_level = Level.objects.create(school=other_school, name='Primary', is_system_generated=False)
        other_class = ClassLevel.objects.create(school=other_school, level=other_level, name='Basic 1', is_system_generated=False)
        ensure_default_stream(other_class)
        AcademicYear.objects.create(school=other_school, academic_year='2025/2026', start_date='2025-09-01', end_date='2026-07-31', is_active=True)
        year = AcademicYear.objects.get(school=other_school)
        Term.objects.create(school=other_school, academic_year=year, term=Term.TermChoices.FIRST_TERM, start_date='2025-09-01', end_date='2025-12-15', is_active=True)
        client = APIClient()
        set_client_auth_cookies(client, other)
        created = client.post(reverse('migration-job-list'), {'job_type': 'student_enrollment', 'template': 'student_information', 'source_system': 'Legacy'}, format='json')
        uploaded = client.post(
            reverse('migration-job-upload', kwargs={'job_id': created.data['id']}),
            {'file': SimpleUploadedFile('pupils.csv', b'First name,Last name,Gender,Date of birth,Admission date,Class\nAma,Mensah,female,2010-01-15,2025-09-01,Primary 1\n', content_type='text/csv')},
            format='multipart',
        )
        sheet_id = uploaded.data['sheets'][0]['id']
        suggestions = client.get(reverse('migration-sheet-suggest', kwargs={'job_id': created.data['id'], 'sheet_id': sheet_id}))
        client.put(
            reverse('migration-sheet-mapping', kwargs={'job_id': created.data['id'], 'sheet_id': sheet_id}),
            {'mappings': suggestions.data['suggestions']},
            format='json',
        )
        client.post(reverse('migration-job-validate', kwargs={'job_id': created.data['id']}))
        other_classes = client.get(reverse('migration-class-resolution', kwargs={'job_id': created.data['id']})).data['classes']
        self.assertEqual(other_classes[0]['status'], 'unresolved')
        self.assertFalse(SchoolValueMapping.objects.filter(school=other_school, field_name='class_name').exists())

    def test_approved_gender_is_reused_for_the_same_school_only(self):
        content = (
            'First name,Last name,Gender,Date of birth,Admission date\n'
            'Ama,Mensah,Boy,2010-01-15,2025-09-01\n'
        )
        job_id, _suggestions = self.upload('student_information', content)
        values = self.client.get(reverse('migration-value-reconciliation', kwargs={'job_id': job_id})).data['fields']
        gender = next(item for item in values if item['field'] == 'gender')['values'][0]
        self.assertEqual(gender['status'], 'suggested')
        self.client.post(
            reverse('migration-value-reconciliation', kwargs={'job_id': job_id}),
            {'values': [{'field': 'gender', 'source_value': gender['source_value'], 'label': 'Boy', 'canonical_value': 'male'}]},
            format='json',
        )
        again, _suggestions = self.upload('student_information', content.replace('Ama', 'Kojo'))
        reused = self.preview(again)['rows'][0]
        self.assertEqual(reused['transformed_values']['gender'], 'male')
        self.assertFalse(reused['proposal']['blocked'])

    def test_enrollment_history_does_not_create_students_and_keeps_a_snapshot(self):
        create_student(school=self.school, student_id='STU-1', first_name='Ama')
        job_id, _suggestions = self.upload(
            'enrollment_history',
            'Student ID,Academic year,Term,Class\n'
            'STU-1,2020/2021,first,Old Form 1\n'
            'MISSING,2020/2021,first,Old Form 1\n',
        )
        preview = {row['transformed_values']['student_id']: row for row in self.preview(job_id)['rows']}
        self.assertEqual(preview['STU-1']['proposal']['enrollment']['action'], 'needs_year')
        self.assertTrue(preview['MISSING']['proposal']['blocked'])
        dated = self.client.post(
            reverse('migration-year-plan', kwargs={'job_id': job_id}),
            {'label': '2020/2021', 'start_date': '2020-09-01', 'end_date': '2021-07-31'},
            format='json',
        )
        self.assertEqual(dated.status_code, status.HTTP_200_OK, dated.data)
        committed = self.client.post(
            reverse('migration-job-commit', kwargs={'job_id': job_id}),
            {'confirm': True},
            format='json',
        )
        self.assertEqual(committed.status_code, status.HTTP_200_OK, committed.data)
        historical = AcademicYear.objects.get(school=self.school, academic_year='2020/2021')
        self.assertFalse(historical.is_active)
        self.assertEqual(historical.terms.count(), 3)
        self.year.refresh_from_db()
        self.assertTrue(self.year.is_active)
        snapshot = ClassLevel.objects.get(school=self.school, name='Old Form 1')
        self.assertTrue(snapshot.is_migration_snapshot)
        self.assertFalse(Student.objects.filter(student_id='MISSING').exists())
        self.assertEqual(Student.objects.get(student_id='STU-1').enrollments.get().class_resolution, 'snapshot')
        self.assertEqual(StudentFee.objects.count(), 0)
        self.assertEqual(MigrationJob.objects.get(pk=job_id).template, 'enrollment_history')

    def test_ambiguous_class_needs_a_choice(self):
        level = ClassLevel.objects.create(school=self.school, level=self.level, name='JHS 2', is_system_generated=False)
        ClassStream.objects.create(class_level=level, name='A', is_default=False)
        ClassStream.objects.create(class_level=level, name='B', is_default=False)
        job_id, _suggestions = self.upload(
            'student_information',
            'First name,Last name,Gender,Date of birth,Admission date,Class\n'
            'Ama,Mensah,female,2010-01-15,2025-09-01,JHS 2\n',
        )
        classes = self.client.get(reverse('migration-class-resolution', kwargs={'job_id': job_id})).data['classes']
        self.assertEqual(classes[0]['status'], 'unresolved')
        self.assertTrue(classes[0]['needs_confirmation'])
        self.assertGreater(len(classes[0]['options']), 1)
        self.assertTrue(self.preview(job_id)['rows'][0]['proposal']['blocked'])
        self.assertEqual(MigrationRow.objects.filter(job_id=job_id).get().raw_values['Class'], 'JHS 2')

    def test_needs_attention_row_can_be_corrected_and_downloaded(self):
        job_id, _suggestions = self.upload(
            'student_information',
            'First name,Last name,Gender,Date of birth,Admission date\n'
            'Ama,Mensah,female,not-a-date,2025-09-01\n',
        )
        report = self.client.get(reverse('migration-attention-report', kwargs={'job_id': job_id}))
        self.assertEqual(report.status_code, status.HTTP_200_OK)
        self.assertIn('Student information - Legacy needs-attention.csv', report['Content-Disposition'])
        downloaded = report.content.decode()
        self.assertIn('First name', downloaded)
        self.assertIn('Ama', downloaded)
        self.assertIn('not-a-date', downloaded)
        plan = self.client.get(reverse('migration-job-plan', kwargs={'job_id': job_id}))
        row = plan.data['rows'][0]
        self.assertEqual(row['validation_status'], 'blocked')
        form = self.client.get(reverse('migration-row-correction', kwargs={'job_id': job_id, 'row_id': row['id']}))
        field_keys = [item['key'] for item in form.data['fields']]
        self.assertIn('date_of_birth', field_keys)
        self.assertIn('first_name', field_keys)
        self.assertIn('guardian_phone', field_keys)
        self.assertIn('stream_id', field_keys)
        saved = self.client.post(
            reverse('migration-row-correction', kwargs={'job_id': job_id, 'row_id': row['id']}),
            {'values': {
                'first_name': 'Ama',
                'last_name': 'Mensah',
                'gender': 'female',
                'date_of_birth': '17 Nov 2010',
                'admission_date': '2025-09-01',
            }},
            format='json',
        )
        self.assertEqual(saved.status_code, status.HTTP_200_OK, saved.data)
        self.assertEqual(saved.data['validation_status'], 'ready')
        self.assertEqual(saved.data['transformed_values']['date_of_birth'], '2010-11-17')
        self.assertEqual(saved.data['raw_values']['Date of birth'], 'not-a-date')

        class_job, _suggestions = self.upload(
            'student_information',
            'First name,Last name,Gender,Date of birth,Admission date,Class\n'
            'Kojo,Asare,male,2010-01-15,2025-09-01,Form 9\n',
        )
        class_plan = self.client.get(reverse('migration-job-plan', kwargs={'job_id': class_job}))
        class_row = class_plan.data['rows'][0]
        self.assertTrue(class_row['proposal']['blocked'])
        corrected = self.client.post(
            reverse('migration-row-correction', kwargs={'job_id': class_job, 'row_id': class_row['id']}),
            {'values': {'stream_id': str(self.stream.id)}},
            format='json',
        )
        self.assertEqual(corrected.status_code, status.HTTP_200_OK, corrected.data)
        self.assertEqual(corrected.data['validation_status'], 'ready')
        self.assertEqual(corrected.data['proposal']['enrollment']['stream_id'], str(self.stream.id))
        self.assertEqual(corrected.data['raw_values']['Class'], 'Form 9')

    def test_edit_form_shows_known_select_values(self):
        job_id, _suggestions = self.upload(
            'student_information',
            'First name,Last name,Gender,Date of birth,Admission date,New student,Relationship,Class\n'
            'Ama,Mensah,female,not-a-date,2025-09-01,Yes,Mother,JHS 1 A\n',
        )
        row = MigrationRow.objects.get(job_id=job_id)
        form = self.client.get(reverse('migration-row-correction', kwargs={'job_id': job_id, 'row_id': row.id}))
        shown = {item['key']: item['value'] for item in form.data['fields']}
        self.assertEqual(shown['is_new_student'], 'yes')
        self.assertEqual(shown['guardian_relationship'], 'mother')
        self.assertEqual(shown['stream_id'], str(self.stream_a.id))
        self.assertEqual(shown['admission_date'], '2025-09-01')
        self.assertEqual(shown['date_of_birth'], '')

    def test_unmatched_relationship_can_be_left_out(self):
        content = (
            'First name,Last name,Gender,Date of birth,Admission date,Relationship\n'
            'Ama,Mensah,female,2010-01-15,2025-09-01,Continuing\n'
        )
        job_id, _suggestions = self.upload('student_information', content)
        plan = self.client.get(reverse('migration-job-plan', kwargs={'job_id': job_id}))
        self.assertTrue(plan.data['rows'][0]['proposal']['blocked'])
        groups = self.client.get(reverse('migration-value-reconciliation', kwargs={'job_id': job_id})).data['fields']
        relationship = next(group for group in groups if group['field'] == 'guardian_relationship')
        self.assertTrue(relationship['can_omit'])
        continuing = next(item for item in relationship['values'] if item['label'] == 'Continuing')
        saved = self.client.post(
            reverse('migration-value-reconciliation', kwargs={'job_id': job_id}),
            {'values': [{
                'field': 'guardian_relationship',
                'source_value': continuing['source_value'],
                'label': 'Continuing',
                'canonical_value': '__omit__',
            }]},
            format='json',
        )
        self.assertEqual(saved.status_code, status.HTTP_200_OK, saved.data)
        left = next(item for item in saved.data['fields'] if item['field'] == 'guardian_relationship')
        self.assertEqual(left['values'][0]['status'], 'omitted')
        row = MigrationRow.objects.get(job_id=job_id)
        self.assertEqual(row.validation_status, MigrationRow.ValidationStatus.READY)
        self.assertFalse(row.transformed_values.get('guardian_relationship'))
        self.assertEqual(row.raw_values['Relationship'], 'Continuing')

        gender = self.client.post(
            reverse('migration-value-reconciliation', kwargs={'job_id': job_id}),
            {'values': [{
                'field': 'gender',
                'source_value': 'female',
                'label': 'female',
                'canonical_value': '__omit__',
            }]},
            format='json',
        )
        self.assertEqual(gender.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unfinished_import_can_be_deleted_and_a_saved_one_cannot(self):
        created = self.client.post(
            reverse('migration-job-list'),
            {'job_type': 'student_enrollment', 'template': 'student_information', 'source_system': 'Legacy'},
            format='json',
        )
        job_id = created.data['id']
        deleted = self.client.delete(reverse('migration-job-detail', kwargs={'job_id': job_id}))
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(MigrationJob.objects.filter(pk=job_id).exists())

        again = self.client.post(
            reverse('migration-job-list'),
            {'job_type': 'student_enrollment', 'template': 'student_information', 'source_system': 'Legacy'},
            format='json',
        )
        saved = MigrationJob.objects.get(pk=again.data['id'])
        saved.status = MigrationJob.Status.COMMITTED
        saved.save(update_fields=['status'])
        blocked = self.client.delete(reverse('migration-job-detail', kwargs={'job_id': saved.id}))
        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(MigrationJob.objects.filter(pk=saved.id).exists())
