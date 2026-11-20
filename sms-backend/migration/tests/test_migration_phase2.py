from datetime import date
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from academics.models import ClassLevel, ClassStream, Level
from academics.services.all_classes import get_all_classes
from accounts.models import User
from accounts.tests.factories import create_membership, create_user, set_client_auth_cookies, user_school
from billing.models import Plan
from billing.services.capacity import active_student_count, ensure_can_add_students
from billing.services.catalog import seed_default_plans
from billing.services.subscriptions import start_subscription
from fees.models import FeeStructure, Payment, StudentFee
from migration.models import ExternalStudentReference, MigrationCommitRecord, MigrationFile, MigrationJob, MigrationRow
from migration.services.student_commit import process_student_commit
from schools.models import AcademicYear, Term
from students.models import ClassEnrollment, Parent, Student, StudentParent
from students.services import clear_student_graduation
from students.tests.factories import create_student, ensure_default_stream


class StudentMigrationTests(APITestCase):
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

    def upload_student_csv(self, content):
        created = self.client.post(
            reverse('migration-job-list'),
            {'job_type': 'student_enrollment', 'source_system': 'Legacy'},
            format='json',
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        job_id = created.data['id']
        from django.core.files.uploadedfile import SimpleUploadedFile

        uploaded = self.client.post(
            reverse('migration-job-upload', kwargs={'job_id': job_id}),
            {'file': SimpleUploadedFile('pupils.csv', content.encode(), content_type='text/csv')},
            format='multipart',
        )
        self.assertEqual(uploaded.status_code, status.HTTP_201_CREATED, uploaded.data)
        sheet_id = uploaded.data['sheets'][0]['id']
        headers = uploaded.data['sheets'][0]['detected_headers']
        suggestions = self.client.get(reverse(
            'migration-sheet-suggest',
            kwargs={'job_id': job_id, 'sheet_id': sheet_id},
        ))
        saved = self.client.put(
            reverse('migration-sheet-mapping', kwargs={'job_id': job_id, 'sheet_id': sheet_id}),
            {'mappings': suggestions.data['suggestions']},
            format='json',
        )
        self.assertEqual(saved.status_code, status.HTTP_200_OK, saved.data)
        validated = self.client.post(reverse('migration-job-validate', kwargs={'job_id': job_id}))
        self.assertEqual(validated.status_code, status.HTTP_200_OK, validated.data)
        preview = self.client.get(reverse('migration-job-preview', kwargs={'job_id': job_id}))
        return job_id, preview.data

    def commit(self, job_id):
        response = self.client.post(
            reverse('migration-job-commit', kwargs={'job_id': job_id}),
            {'confirm': True},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response

    def test_exact_student_id_fills_empty_fields_and_keeps_conflicts(self):
        student = create_student(
            school=self.school,
            student_id='STU-1',
            first_name='Ama',
            last_name='Mensah',
        )
        student.address = ''
        student.save(update_fields=['address', 'updated_at'])
        job_id, preview = self.upload_student_csv(
            'Student ID,First Name,Last Name,Gender,Date of Birth,Admission Date,Address,Class,Academic Year,Term\n'
            'STU-1,Ama,Boateng,female,2010-01-15,2025-09-01,Accra,JHS 1,2025/2026,first_term\n'
        )
        row = preview['rows'][0]
        self.assertEqual(row['proposal']['action'], 'link')
        self.assertEqual(row['proposal']['match_kind'], 'exact')
        self.assertTrue(row['proposal']['blocked'])
        self.client.post(
            reverse('migration-row-review', kwargs={'job_id': job_id, 'row_id': row['id']}),
            {'resolutions': {'last_name': 'keep', 'date_of_birth': 'keep', 'admission_date': 'keep', 'gender': 'keep'}},
            format='json',
        )
        self.commit(job_id)
        student.refresh_from_db()
        self.assertEqual(student.last_name, 'Mensah')
        self.assertEqual(student.address, 'Accra')
        self.assertEqual(Student.objects.filter(school=self.school).count(), 1)
        self.assertEqual(ClassEnrollment.objects.filter(student=student, term=self.term).count(), 1)
        self.assertEqual(StudentFee.objects.count(), 0)
        self.assertEqual(Payment.objects.count(), 0)
        self.assertEqual(FeeStructure.objects.count(), 0)

    def test_external_reference_links_and_probable_match_needs_confirmation(self):
        student = create_student(school=self.school, student_id='KEEP')
        ExternalStudentReference.objects.create(
            school=self.school,
            source_system='Legacy',
            external_id='LEG-9',
            student=student,
        )
        job_id, preview = self.upload_student_csv(
            'External ID,First Name,Last Name,Gender,Date of Birth,Admission Date\n'
            'LEG-9,Ama,Mensah,female,2010-01-15,2025-09-01\n'
        )
        self.assertEqual(preview['rows'][0]['proposal']['match_reason'], 'External student reference.')
        self.commit(job_id)
        self.assertEqual(Student.objects.filter(school=self.school).count(), 1)

        other = create_student(
            school=self.school,
            student_id='STU-2',
            first_name='Kojo',
            last_name='Asare',
            date_of_birth=date(2012, 2, 2),
        )
        probable_job, probable = self.upload_student_csv(
            'First Name,Last Name,Gender,Date of Birth,Admission Date\n'
            'Kojo,Asare,male,2012-02-02,2025-09-01\n'
        )
        row = probable['rows'][0]
        self.assertEqual(row['proposal']['match_kind'], 'probable')
        self.assertTrue(row['proposal']['blocked'])
        self.commit(probable_job)
        self.assertEqual(Student.objects.filter(first_name='Kojo').count(), 1)
        self.client.post(
            reverse('migration-row-match', kwargs={'job_id': probable_job, 'row_id': row['id']}),
            {'decision': 'create'},
            format='json',
        )
        self.client.post(
            reverse('migration-job-resume', kwargs={'job_id': probable_job}),
            format='json',
        )
        self.assertEqual(Student.objects.filter(first_name='Kojo').count(), 2)
        self.assertEqual(other.student_id, 'STU-2')

    def test_ambiguous_name_and_phone_matches_are_not_merged(self):
        create_student(school=self.school, student_id='A', first_name='Esi', last_name='Owusu', date_of_birth=date(2011, 3, 3))
        create_student(school=self.school, student_id='B', first_name='Esi', last_name='Owusu', date_of_birth=date(2011, 3, 3))
        _job, preview = self.upload_student_csv(
            'First Name,Last Name,Gender,Date of Birth,Admission Date\n'
            'Esi,Owusu,female,2011-03-03,2025-09-01\n'
        )
        self.assertEqual(preview['rows'][0]['proposal']['match_kind'], 'ambiguous')
        self.assertEqual(len(preview['rows'][0]['proposal']['candidates']), 2)

        parent = Parent.objects.create(school=self.school, name='Akosua', phone_number='+233244111222')
        first = create_student(school=self.school, student_id='C', first_name='Yaw', last_name='Boateng')
        second = create_student(school=self.school, student_id='D', first_name='Yaw', last_name='Boateng', date_of_birth=date(2013, 4, 4))
        StudentParent.objects.create(student=first, parent=parent, relationship='mother', is_primary=True)
        StudentParent.objects.create(student=second, parent=parent, relationship='mother', is_primary=True)
        _phone_job, phone_preview = self.upload_student_csv(
            'First Name,Last Name,Gender,Date of Birth,Admission Date,Guardian Phone\n'
            'Yaw,Boateng,male,2014-05-05,2025-09-01,0244111222\n'
        )
        self.assertEqual(phone_preview['rows'][0]['proposal']['match_kind'], 'ambiguous')
        self.assertIn('guardian phone', phone_preview['rows'][0]['proposal']['match_reason'])

    def test_guardian_reuse_creation_and_primary_protection(self):
        parent = Parent.objects.create(school=self.school, name='Akosua Mensah', phone_number='+233244111222')
        student = create_student(school=self.school, student_id='STU-9')
        StudentParent.objects.create(student=student, parent=parent, relationship='mother', is_primary=True)
        job_id, preview = self.upload_student_csv(
            'Student ID,First Name,Last Name,Gender,Date of Birth,Admission Date,Guardian Name,Guardian Phone\n'
            'STU-9,Ama,Mensah,female,2010-01-15,2025-09-01,Akosua Mensah,0244111222\n'
            'STU-10,Kojo,Mensah,male,2011-01-01,2025-09-01,Kofi Mensah,0200000000\n'
        )
        actions = {row['transformed_values']['student_id']: row['proposal']['guardian']['action'] for row in preview['rows']}
        self.assertEqual(actions['STU-9'], 'already_linked')
        self.assertEqual(actions['STU-10'], 'create')
        self.commit(job_id)
        self.assertEqual(Parent.objects.filter(school=self.school).count(), 2)
        created = Student.objects.get(student_id='STU-10')
        self.assertEqual(created.parent_links.get().parent.phone_number, '+233200000000')
        self.assertEqual(student.parent_links.count(), 1)

        conflict_job, conflict = self.upload_student_csv(
            'Student ID,First Name,Last Name,Gender,Date of Birth,Admission Date,Guardian Name,Guardian Phone\n'
            'STU-9,Ama,Mensah,female,2010-01-15,2025-09-01,New Person,0200000000\n'
        )
        row = conflict['rows'][0]
        self.assertEqual(row['proposal']['guardian']['action'], 'review')
        self.client.post(
            reverse('migration-row-review', kwargs={'job_id': conflict_job, 'row_id': row['id']}),
            {'guardian_decision': 'keep'},
            format='json',
        )
        self.commit(conflict_job)
        self.assertEqual(student.parent_links.filter(is_primary=True).get().parent_id, parent.id)
        self.assertEqual(student.parent_links.count(), 1)

    def test_historical_year_snapshot_and_current_class_rules(self):
        job_id, preview = self.upload_student_csv(
            'First Name,Last Name,Gender,Date of Birth,Admission Date,Class,Academic Year,Term,Graduated\n'
            'Ama,Mensah,female,2010-01-15,2020-09-01,Old Form 1,2020/2021,first,yes\n'
            'Kojo,Mensah,male,2011-01-01,2025-09-01,Unknown Class,2025/2026,first,no\n'
            'Esi,Mensah,female,2012-01-01,2025-09-01,JHS 1,2025/2026,first,no\n'
        )
        by_name = {row['transformed_values']['first_name']: row for row in preview['rows']}
        self.assertEqual(by_name['Ama']['proposal']['enrollment']['action'], 'needs_year')
        self.assertTrue(by_name['Kojo']['proposal']['blocked'])
        self.assertEqual(by_name['Esi']['proposal']['enrollment']['action'], 'current')
        outside = self.client.post(
            reverse('migration-year-plan', kwargs={'job_id': job_id}),
            {'label': '2020/2021', 'start_date': '2019-09-01', 'end_date': '2021-07-31'},
            format='json',
        )
        self.assertEqual(outside.status_code, status.HTTP_400_BAD_REQUEST, outside.data)
        self.assertIn('2020', str(outside.data))
        late = self.client.post(
            reverse('migration-year-plan', kwargs={'job_id': job_id}),
            {'label': '2020/2021', 'start_date': '2020-09-01', 'end_date': '2022-07-31'},
            format='json',
        )
        self.assertEqual(late.status_code, status.HTTP_400_BAD_REQUEST, late.data)
        self.assertIn('2021', str(late.data))
        dated = self.client.post(
            reverse('migration-year-plan', kwargs={'job_id': job_id}),
            {'label': '2020/2021', 'start_date': '2020-09-01', 'end_date': '2021-07-31'},
            format='json',
        )
        self.assertEqual(dated.status_code, status.HTTP_200_OK, dated.data)
        self.commit(job_id)
        historical = AcademicYear.objects.get(school=self.school, academic_year='2020/2021')
        self.assertFalse(historical.is_active)
        self.assertEqual(historical.terms.count(), 3)
        self.assertFalse(historical.terms.filter(is_active=True).exists())
        self.year.refresh_from_db()
        self.term.refresh_from_db()
        self.assertTrue(self.year.is_active)
        self.assertTrue(self.term.is_active)
        snapshot = ClassLevel.objects.get(school=self.school, name='Old Form 1')
        self.assertTrue(snapshot.is_migration_snapshot)
        self.assertFalse(snapshot.is_active)
        self.assertFalse(snapshot.level.is_active)
        names = [
            item['display_name']
            for level in get_all_classes(school=self.school)['levels']
            for item in level['classes']
        ]
        self.assertNotIn('Old Form 1', names)
        self.assertFalse(
            ClassLevel.objects.filter(
                school=self.school,
                is_migration_snapshot=False,
                level__is_migration_snapshot=False,
                name='Old Form 1',
            ).exists(),
        )
        graduate = Student.objects.get(first_name='Ama', last_name='Mensah')
        self.assertTrue(graduate.is_graduated)
        self.assertEqual(graduate.enrollments.get().class_resolution, 'snapshot')
        self.assertTrue(graduate.enrollments.get().is_new_student)
        current = Student.objects.get(first_name='Esi')
        self.assertEqual(current.enrollments.get().stream_id, self.stream.id)
        self.assertFalse(Student.objects.filter(first_name='Kojo').exists())
        self.assertEqual(StudentFee.objects.count(), 0)

    def test_commit_requires_confirmation_and_stays_inside_the_school(self):
        job_id, _preview = self.upload_student_csv(
            'First Name,Last Name,Gender,Date of Birth,Admission Date\n'
            'Ama,Mensah,female,2010-01-15,2025-09-01\n'
        )
        missing = self.client.post(reverse('migration-job-commit', kwargs={'job_id': job_id}), {}, format='json')
        self.assertEqual(missing.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Student.objects.count(), 0)
        other = create_user(phone_number='+233244567891', email='other@test.com', is_active=True)
        client = APIClient()
        set_client_auth_cookies(client, other)
        denied = client.post(
            reverse('migration-job-commit', kwargs={'job_id': job_id}),
            {'confirm': True},
            format='json',
        )
        self.assertEqual(denied.status_code, status.HTTP_404_NOT_FOUND)
        accountant = User.objects.create(
            phone_number='+233200000088',
            email='acct2@test.com',
            first_name='Ama',
            last_name='Owusu',
            is_active=True,
        )
        accountant.set_unusable_password()
        accountant.save(update_fields=['password'])
        create_membership(accountant, self.school, role=User.RoleChoices.ACCOUNTANT)
        accountant_client = APIClient()
        set_client_auth_cookies(accountant_client, accountant, self.school)
        forbidden = accountant_client.get(reverse('migration-job-plan', kwargs={'job_id': job_id}))
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

    def test_retry_is_idempotent_and_a_failed_row_does_not_roll_back_the_other(self):
        job_id, preview = self.upload_student_csv(
            'First Name,Last Name,Gender,Date of Birth,Admission Date,Guardian Phone\n'
            'Ama,Mensah,female,2010-01-15,2025-09-01,0244000001\n'
            'Kojo,Mensah,male,2011-01-01,2025-09-01,0244000002\n'
        )
        real_guardian = __import__(
            'migration.services.student_commit',
            fromlist=['_apply_guardian'],
        )._apply_guardian

        def flaky(job, student, values, match):
            if values.get('first_name') == 'Kojo':
                raise RuntimeError('row failed')
            return real_guardian(job, student, values, match)

        with patch('migration.services.student_commit._apply_guardian', side_effect=flaky):
            self.commit(job_id)
        self.assertEqual(Student.objects.filter(first_name='Ama').count(), 1)
        self.assertFalse(Student.objects.filter(first_name='Kojo').exists())
        self.assertEqual(MigrationCommitRecord.objects.count(), 1)
        job = MigrationJob.objects.get(pk=job_id)
        self.assertEqual(job.status, MigrationJob.Status.PARTIALLY_COMMITTED)
        resumed = self.client.post(reverse('migration-job-resume', kwargs={'job_id': job_id}))
        self.assertEqual(resumed.status_code, status.HTTP_200_OK, resumed.data)
        self.assertEqual(Student.objects.filter(first_name='Kojo').count(), 1)
        self.assertEqual(Parent.objects.filter(phone_number='+233244000001').count(), 1)
        process_student_commit(job_id)
        self.assertEqual(Student.objects.count(), 2)
        self.assertEqual(ClassEnrollment.objects.count(), 0)

    def test_continue_keeps_a_blocked_row_and_finish_leaves_it_out(self):
        job_id, _preview = self.upload_student_csv(
            'Student ID,First Name,Last Name,Gender,Date of Birth,Admission Date\n'
            'LEG-1,Ama,Mensah,female,2010-01-15,2025-09-01\n'
            'LEG-2,Kojo,Mensah,male,2011-01-01,2025-09-01\n'
        )
        real_guardian = __import__(
            'migration.services.student_commit',
            fromlist=['_apply_guardian'],
        )._apply_guardian

        def flaky(job, student, values, match):
            if values.get('first_name') == 'Kojo':
                raise RuntimeError('row failed')
            return real_guardian(job, student, values, match)

        with patch('migration.services.student_commit._apply_guardian', side_effect=flaky):
            self.commit(job_id)
        row = MigrationRow.objects.get(job_id=job_id, transformed_values__first_name='Kojo')
        row.validation_status = MigrationRow.ValidationStatus.BLOCKED
        row.proposal = {
            **(row.proposal or {}),
            'blocked': True,
            'student_label': 'Kojo Mensah',
            'block_reasons': [{
                'column': 'student_id',
                'message': 'Student ID LEG-2 is used more than once in this file. Change it on one of these rows before saving.',
            }],
        }
        row.errors = row.proposal['block_reasons']
        row.save(update_fields=['validation_status', 'proposal', 'errors', 'updated_at'])

        resumed = self.client.post(reverse('migration-job-resume', kwargs={'job_id': job_id}))
        self.assertEqual(resumed.status_code, status.HTTP_400_BAD_REQUEST, resumed.data)
        row.refresh_from_db()
        self.assertEqual(row.commit_status, MigrationRow.CommitStatus.FAILED)
        self.assertEqual(MigrationJob.objects.get(pk=job_id).status, MigrationJob.Status.PARTIALLY_COMMITTED)
        self.assertTrue(MigrationFile.objects.get(job_id=job_id).storage_key)
        self.assertFalse(Student.objects.filter(first_name='Kojo').exists())

        finished = self.client.post(reverse('migration-job-finish', kwargs={'job_id': job_id}))
        self.assertEqual(finished.status_code, status.HTTP_200_OK, finished.data)
        self.assertEqual(finished.data['status'], MigrationJob.Status.COMMITTED)
        row.refresh_from_db()
        self.assertEqual(row.commit_status, MigrationRow.CommitStatus.SKIPPED)
        stored = MigrationFile.objects.get(job_id=job_id)
        self.assertEqual(stored.storage_key, '')
        self.assertEqual(stored.original_filename, 'pupils.csv')
        self.assertEqual(Student.objects.filter(first_name='Ama').count(), 1)
        self.assertFalse(Student.objects.filter(first_name='Kojo').exists())
        saved_page = self.client.get(reverse('migration-job-plan', kwargs={'job_id': job_id}), {'outcome': 'saved'})
        self.assertEqual(saved_page.status_code, status.HTTP_200_OK, saved_page.data)
        self.assertEqual(saved_page.data['count'], 1)
        self.assertEqual(saved_page.data['saved_count'], 1)
        self.assertEqual(saved_page.data['total_count'], 2)
        self.assertEqual(saved_page.data['results'][0]['transformed_values']['first_name'], 'Ama')
        unsaved_page = self.client.get(
            reverse('migration-job-plan', kwargs={'job_id': job_id}),
            {'outcome': 'unsaved', 'page': 2},
        )
        self.assertEqual(unsaved_page.data['count'], 1)
        self.assertEqual(unsaved_page.data['page'], 1)
        self.assertEqual(unsaved_page.data['results'][0]['transformed_values']['first_name'], 'Kojo')

    def test_interrupted_batch_does_not_duplicate_students(self):
        job_id, _preview = self.upload_student_csv(
            'First Name,Last Name,Gender,Date of Birth,Admission Date\n'
            'Ama,Mensah,female,2010-01-15,2025-09-01\n'
        )
        self.client.post(
            reverse('migration-job-commit', kwargs={'job_id': job_id}),
            {'confirm': True},
            format='json',
        )
        self.assertEqual(Student.objects.count(), 1)

        def explode(**kwargs):
            raise RuntimeError('worker stopped')

        MigrationJob.objects.filter(pk=job_id).update(
            status=MigrationJob.Status.COMMITTING,
            heartbeat_at=None,
        )
        MigrationRow.objects.filter(job_id=job_id).update(commit_status='pending')
        MigrationCommitRecord.objects.all().delete()
        Student.objects.all().delete()
        with patch('migration.services.student_commit.MigrationJob.objects.filter', side_effect=explode):
            with self.assertRaises(RuntimeError):
                process_student_commit(job_id)
        self.assertEqual(Student.objects.count(), 0)
        process_student_commit(job_id)
        self.assertEqual(Student.objects.count(), 1)
        process_student_commit(job_id)
        self.assertEqual(Student.objects.count(), 1)

    def test_capacity_ignores_graduates_and_inactive_students(self):
        seed_default_plans()
        starter = Plan.objects.get(code='starter')
        start_subscription(school=self.school, plan=starter, apply_first_year_free=True)
        starter.student_max = 1
        starter.save(update_fields=['student_max', 'updated_at'])
        create_student(school=self.school, student_id='ACTIVE')
        graduated = create_student(school=self.school, student_id='GRAD')
        graduated.is_graduated = True
        graduated.save(update_fields=['is_graduated', 'updated_at'])
        inactive = create_student(school=self.school, student_id='LEFT')
        inactive.is_active = False
        inactive.save(update_fields=['is_active', 'updated_at'])
        self.assertEqual(active_student_count(self.school), 1)
        with self.assertRaises(Exception):
            ensure_can_add_students(self.school, additional=1)
        with self.assertRaises(Exception):
            clear_student_graduation(school=self.school, student_id=graduated.id)
        graduated.refresh_from_db()
        self.assertTrue(graduated.is_graduated)
