from datetime import date
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import load_workbook
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.models import User
from accounts.tests.factories import create_membership, create_user, set_client_auth_cookies, user_school
from fees.models import FeeItem, FeeStructure, Payment, PaymentAllocation, Receipt, StudentFee, StudentFeeCredit
from fees.services.fees import (
    apply_fee_structure,
    carry_forward_fee_structure,
    ensure_enrollment_fees,
    get_student_term_balance,
    publish_fee_structure,
)
from fees.services.desk import list_fee_desk_debtor_ids, list_fee_desk_rows
from fees.services.settings import serialize_structure_detail
from migration.models import ExternalStudentReference, MigrationJob, MigrationOpeningBalance, MigrationRow
from migration.services.opening_commit import process_opening_commit
from schools.models import AcademicYear, Term
from students.models import Student
from students.services import create_class_enrollment
from students.tests.factories import create_student, ensure_default_stream
from academics.models import ClassLevel, Level


class OpeningBalanceMigrationTests(APITestCase):
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
        self.second_term = Term.objects.create(
            school=self.school,
            academic_year=self.year,
            term=Term.TermChoices.SECOND_TERM,
            start_date='2025-12-16',
            end_date='2026-03-31',
            is_active=False,
        )
        self.third_term = Term.objects.create(
            school=self.school,
            academic_year=self.year,
            term=Term.TermChoices.THIRD_TERM,
            start_date='2026-04-01',
            end_date='2026-07-31',
            is_active=False,
        )
        self.past_year = AcademicYear.objects.create(
            school=self.school,
            academic_year='2024/2025',
            start_date='2024-09-01',
            end_date='2025-07-31',
            is_active=False,
        )
        self.past_term = Term.objects.create(
            school=self.school,
            academic_year=self.past_year,
            term=Term.TermChoices.FIRST_TERM,
            start_date='2024-09-01',
            end_date='2024-12-15',
            is_active=False,
        )
        Term.objects.create(
            school=self.school,
            academic_year=self.past_year,
            term=Term.TermChoices.SECOND_TERM,
            start_date='2024-12-16',
            end_date='2025-03-31',
            is_active=False,
        )
        Term.objects.create(
            school=self.school,
            academic_year=self.past_year,
            term=Term.TermChoices.THIRD_TERM,
            start_date='2025-04-01',
            end_date='2025-07-31',
            is_active=False,
        )
        self.level = Level.objects.create(school=self.school, name='Junior High', is_system_generated=False)
        self.class_level = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='JHS 1',
            is_system_generated=False,
        )
        self.stream = ensure_default_stream(self.class_level)

    def upload(self, content, source_system='Legacy'):
        created = self.client.post(
            reverse('migration-job-list'),
            {
                'job_type': 'fee_financial_history',
                'template': 'opening_balances',
                'source_system': source_system,
            },
            format='json',
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        job_id = created.data['id']
        uploaded = self.client.post(
            reverse('migration-job-upload', kwargs={'job_id': job_id}),
            {'file': SimpleUploadedFile('balances.csv', content.encode(), content_type='text/csv')},
            format='multipart',
        )
        self.assertEqual(uploaded.status_code, status.HTTP_201_CREATED, uploaded.data)
        sheet_id = uploaded.data['sheets'][0]['id']
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
        preview = self.client.get(reverse('migration-job-plan', kwargs={'job_id': job_id}))
        self.assertEqual(preview.status_code, status.HTTP_200_OK, preview.data)
        return job_id, preview.data

    def commit(self, job_id, total):
        return self.client.post(
            reverse('migration-job-commit', kwargs={'job_id': job_id}),
            {'confirm': True, 'confirmed_total': total},
            format='json',
        )

    def test_template_csv_and_xlsx_headers(self):
        xlsx = self.client.get(reverse('migration-template', kwargs={'template': 'opening_balances'}))
        self.assertEqual(xlsx.status_code, status.HTTP_200_OK)
        workbook = load_workbook(BytesIO(xlsx.content))
        self.assertEqual(
            [cell.value for cell in workbook['Opening balances'][1]],
            ['Student ID', 'Academic year', 'Term', 'Outstanding balance', 'Source reference', 'Notes'],
        )
        csv_file = self.client.get(
            reverse('migration-template', kwargs={'template': 'opening_balances'}),
            {'file': 'csv'},
        )
        self.assertTrue(csv_file.content.decode().startswith(
            'Student ID,Academic year,Term,Outstanding balance,Source reference,Notes',
        ))

    def test_multiple_terms_years_and_shared_fee_item(self):
        ama = create_student(school=self.school, student_id='STU-1', first_name='Ama', last_name='Mensah')
        kofi = create_student(school=self.school, student_id='STU-2', first_name='Kofi', last_name='Mensah')
        create_class_enrollment(student=ama, term=self.term, stream=self.stream)
        payment = Payment.objects.create(
            student=ama,
            term=self.term,
            amount=Decimal('20.00'),
            payment_method=Payment.PaymentMethod.CASH,
            recorded_by=self.user,
        )
        allocation = payment.allocations.get()
        before_payments = Payment.objects.count()
        before_allocations = list(PaymentAllocation.objects.values_list('id', 'amount', 'term_id'))
        job_id, preview = self.upload(
            'Student ID,Academic year,Term,Outstanding balance,Source reference,Notes\n'
            'STU-1,2025/2026,first,40.00,REF-1,First term\n'
            'STU-1,2025/2026,second,15.50,REF-2,\n'
            'STU-1,2024/2025,first,10.00,REF-3,\n'
            'STU-2,2025/2026,first,25.00,REF-4,\n'
        )
        opening = preview['summary']['opening']
        self.assertEqual(opening['valid_rows'], 4)
        self.assertEqual(opening['unique_students'], 2)
        self.assertEqual(opening['total'], '90.50')
        self.assertEqual(len(opening['by_year']), 2)
        with patch('fees.services.next_term_notices.schedule_next_term_fee_notices_for_structure') as notices, \
                patch('fees.services.next_term_notices.schedule_next_term_fee_notice_for_student') as student_notices, \
                patch('fees.services.credits.apply_available_credits_for_term') as credits:
            saved = self.commit(job_id, '90.50')
            self.assertFalse(notices.called)
            self.assertFalse(student_notices.called)
            self.assertFalse(credits.called)
        self.assertEqual(saved.status_code, status.HTTP_200_OK, saved.data)
        self.assertEqual(saved.data['status'], MigrationJob.Status.COMMITTED)
        self.assertEqual(StudentFee.objects.filter(fee_item__is_migration_opening_balance=True).count(), 4)
        self.assertEqual(Payment.objects.count(), before_payments)
        self.assertEqual(list(PaymentAllocation.objects.values_list('id', 'amount', 'term_id')), before_allocations)
        self.assertEqual(Receipt.objects.count(), 0)
        self.assertEqual(StudentFeeCredit.objects.count(), 0)
        self.assertEqual(MigrationOpeningBalance.objects.count(), 4)
        first_items = FeeItem.objects.filter(
            fee_structure__term=self.term,
            is_migration_opening_balance=True,
        )
        self.assertEqual(first_items.count(), 1)
        self.assertEqual(StudentFee.objects.filter(fee_item=first_items.get()).count(), 2)
        first_balance = get_student_term_balance(student=ama, term=self.term)
        self.assertEqual(first_balance['total_billed'], Decimal('40.00'))
        self.assertEqual(first_balance['balance'], Decimal('20.00'))
        self.assertEqual(get_student_term_balance(student=ama, term=self.second_term)['balance'], Decimal('15.50'))
        self.assertEqual(get_student_term_balance(student=ama, term=self.past_term)['balance'], Decimal('10.00'))
        detail = serialize_structure_detail(first_items.get().fee_structure)
        self.assertNotIn('Opening balance', [item['name'] for item in detail['fee_items']])
        all_time = list_fee_desk_rows(school=self.school, term=self.term, all_time=True)
        ama_row = all_time.get(student=ama)
        self.assertEqual(ama_row.total_billed, Decimal('65.50'))
        active_desk = list_fee_desk_rows(school=self.school, term=self.term, all_time=False)
        self.assertIn(ama.id, list_fee_desk_debtor_ids(queryset=active_desk))
        allocation.refresh_from_db()
        self.assertEqual(allocation.amount, Decimal('20.00'))
        payment.refresh_from_db()
        self.assertEqual(payment.amount, Decimal('20.00'))
        self.year.refresh_from_db()
        self.term.refresh_from_db()
        self.assertTrue(self.year.is_active)
        self.assertTrue(self.term.is_active)

    def test_duplicates_negative_zero_unknown_and_currency(self):
        create_student(school=self.school, student_id='STU-1')
        job_id, preview = self.upload(
            'Student ID,Academic year,Term,Outstanding balance,Currency\n'
            'STU-1,2025/2026,first,10.00,\n'
            'STU-1,2025/2026,first,5.00,\n'
            'STU-9,2025/2026,second,8.00,\n'
            'STU-1,2025/2026,second,-3.00,\n'
            'STU-1,2025/2026,third,0,\n'
            'STU-1,2024/2025,first,12.00,USD\n'
        )
        opening = preview['summary']['opening']
        self.assertEqual(opening['valid_rows'], 0)
        self.assertGreaterEqual(opening['duplicates'], 2)
        self.assertEqual(opening['skipped_rows'], 1)
        messages = ' '.join(
            item.get('message', '')
            for row in preview['rows']
            for item in (row['proposal'].get('block_reasons') or [])
        )
        self.assertIn('not added together', messages)
        self.assertIn('cannot add students', messages)
        self.assertIn('negative', messages.lower())
        self.assertIn('GHS', messages)
        refused = self.commit(job_id, '1.00')
        self.assertEqual(refused.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(StudentFee.objects.count(), 0)
        confirmed = self.commit(job_id, '0.00')
        self.assertEqual(confirmed.status_code, status.HTTP_200_OK, confirmed.data)
        self.assertEqual(StudentFee.objects.count(), 0)
        self.assertEqual(
            MigrationRow.objects.filter(job_id=job_id, commit_status=MigrationRow.CommitStatus.SKIPPED).count(),
            1,
        )

    def test_probable_match_needs_confirmation_and_ambiguous_is_blocked(self):
        ama = create_student(school=self.school, student_id='STU-1', first_name='Ama', last_name='Mensah')
        create_student(
            school=self.school,
            student_id='STU-2',
            first_name='Kojo',
            last_name='Owusu',
            date_of_birth=date(2011, 2, 2),
        )
        create_student(
            school=self.school,
            student_id='STU-3',
            first_name='Kojo',
            last_name='Owusu',
            date_of_birth=date(2011, 2, 2),
        )
        job_id, preview = self.upload(
            'First Name,Last Name,Date of Birth,Academic year,Term,Outstanding balance\n'
            'Ama,Mensah,2010-01-15,2025/2026,first,18.00\n'
            'Kojo,Owusu,2011-02-02,2025/2026,first,9.00\n'
        )
        rows = {row['proposal']['student_label']: row for row in preview['rows']}
        self.assertEqual(rows['Ama Mensah']['proposal']['action'], 'review')
        self.assertEqual(rows['Kojo Owusu']['proposal']['match_kind'], 'ambiguous')
        self.assertTrue(rows['Kojo Owusu']['proposal']['blocked'])
        linked = self.client.post(
            reverse('migration-row-match', kwargs={'job_id': job_id, 'row_id': rows['Ama Mensah']['id']}),
            {'decision': 'link', 'student_id': str(ama.id)},
            format='json',
        )
        self.assertEqual(linked.status_code, status.HTTP_200_OK, linked.data)
        self.assertEqual(linked.data['proposal']['action'], 'balance')
        created = self.client.post(
            reverse('migration-row-match', kwargs={'job_id': job_id, 'row_id': rows['Ama Mensah']['id']}),
            {'decision': 'create'},
            format='json',
        )
        self.assertEqual(created.status_code, status.HTTP_400_BAD_REQUEST)
        saved = self.commit(job_id, '18.00')
        self.assertEqual(saved.status_code, status.HTTP_200_OK, saved.data)
        self.assertEqual(StudentFee.objects.count(), 1)
        self.assertEqual(StudentFee.objects.get().student_id, ama.id)
        self.assertEqual(Student.objects.filter(school=self.school).count(), 3)

    def test_external_reference_links_without_creating_a_student(self):
        ama = create_student(school=self.school, student_id='STU-1')
        ExternalStudentReference.objects.create(
            school=self.school,
            source_system='Legacy',
            external_id='LEG-9',
            student=ama,
        )
        job_id, preview = self.upload(
            'External student ID,Academic year,Term,Outstanding balance\n'
            'LEG-9,2025/2026,second,7.25\n'
        )
        self.assertEqual(preview['rows'][0]['proposal']['action'], 'balance')
        saved = self.commit(job_id, '7.25')
        self.assertEqual(saved.status_code, status.HTTP_200_OK, saved.data)
        self.assertEqual(StudentFee.objects.get().student_id, ama.id)
        self.assertEqual(Student.objects.filter(school=self.school).count(), 1)

    def test_historical_year_stays_inactive(self):
        create_student(school=self.school, student_id='STU-1')
        job_id, preview = self.upload(
            'Student ID,Academic year,Term,Outstanding balance\n'
            'STU-1,2020/2021,first,33.00\n'
        )
        self.assertEqual(preview['rows'][0]['proposal']['enrollment']['action'], 'needs_year')
        planned = self.client.post(
            reverse('migration-year-plan', kwargs={'job_id': job_id}),
            {'label': '2020/2021', 'start_date': '2020-09-01', 'end_date': '2021-07-31'},
            format='json',
        )
        self.assertEqual(planned.status_code, status.HTTP_200_OK, planned.data)
        self.assertEqual(planned.data['opening']['total'], '33.00')
        saved = self.commit(job_id, '33.00')
        self.assertEqual(saved.status_code, status.HTTP_200_OK, saved.data)
        year = AcademicYear.objects.get(school=self.school, academic_year='2020/2021')
        self.assertFalse(year.is_active)
        self.assertEqual(year.terms.count(), 3)
        self.assertFalse(year.terms.filter(is_active=True).exists())
        self.year.refresh_from_db()
        self.term.refresh_from_db()
        self.assertTrue(self.year.is_active)
        self.assertTrue(self.term.is_active)
        self.assertEqual(StudentFee.objects.get().amount, Decimal('33.00'))

    def test_existing_opening_balance_is_not_overwritten(self):
        create_student(school=self.school, student_id='STU-1')
        job_id, _preview = self.upload(
            'Student ID,Academic year,Term,Outstanding balance\n'
            'STU-1,2025/2026,first,10.00\n'
        )
        self.assertEqual(self.commit(job_id, '10.00').status_code, status.HTTP_200_OK)
        second_id, second = self.upload(
            'Student ID,Academic year,Term,Outstanding balance\n'
            'STU-1,2025/2026,first,99.00\n'
        )
        self.assertTrue(second['rows'][0]['proposal']['blocked'])
        self.assertIn('already has an opening balance', second['rows'][0]['proposal']['block_reasons'][0]['message'])
        self.assertEqual(self.commit(second_id, '0.00').status_code, status.HTTP_200_OK)
        self.assertEqual(StudentFee.objects.get().amount, Decimal('10.00'))

    def test_retry_is_idempotent_and_a_failed_row_can_resume(self):
        create_student(school=self.school, student_id='STU-1')
        job_id, _preview = self.upload(
            'Student ID,Academic year,Term,Outstanding balance\n'
            'STU-1,2025/2026,second,12.00\n'
        )
        original = StudentFee.save
        calls = {'count': 0}

        def flaky(fee, *args, **kwargs):
            calls['count'] += 1
            if calls['count'] == 1:
                raise RuntimeError('ledger busy')
            return original(fee, *args, **kwargs)

        with patch.object(StudentFee, 'save', flaky):
            failed = self.commit(job_id, '12.00')
        self.assertEqual(failed.status_code, status.HTTP_200_OK, failed.data)
        self.assertEqual(failed.data['status'], MigrationJob.Status.PARTIALLY_COMMITTED)
        self.assertEqual(StudentFee.objects.count(), 0)
        resumed = self.client.post(reverse('migration-job-resume', kwargs={'job_id': job_id}))
        self.assertEqual(resumed.status_code, status.HTTP_200_OK, resumed.data)
        self.assertEqual(StudentFee.objects.count(), 1)
        row = MigrationRow.objects.get(job_id=job_id)
        row.commit_status = MigrationRow.CommitStatus.PENDING
        row.save(update_fields=['commit_status', 'updated_at'])
        MigrationJob.objects.filter(pk=job_id).update(status=MigrationJob.Status.COMMITTING)
        process_opening_commit(job_id)
        self.assertEqual(StudentFee.objects.count(), 1)
        self.assertEqual(StudentFee.objects.get().amount, Decimal('12.00'))

    def test_a_second_committing_job_is_refused_and_other_schools_cannot_see_it(self):
        create_student(school=self.school, student_id='STU-1')
        job_id, _preview = self.upload(
            'Student ID,Academic year,Term,Outstanding balance\n'
            'STU-1,2025/2026,first,10.00\n'
        )
        MigrationJob.objects.filter(pk=job_id).update(
            status=MigrationJob.Status.COMMITTING,
            heartbeat_at='2026-01-01T00:00:00Z',
        )
        other_id, _other = self.upload(
            'Student ID,Academic year,Term,Outstanding balance\n'
            'STU-1,2025/2026,second,4.00\n'
        )
        refused = self.commit(other_id, '4.00')
        self.assertEqual(refused.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(StudentFee.objects.count(), 0)
        outsider = create_user(
            phone_number='+233244567891',
            email='other-phase3@test.com',
            is_active=True,
        )
        outsider_client = APIClient()
        set_client_auth_cookies(outsider_client, outsider, user_school(outsider))
        hidden = outsider_client.get(reverse('migration-job-detail', kwargs={'job_id': job_id}))
        self.assertEqual(hidden.status_code, status.HTTP_404_NOT_FOUND)

    def test_fee_application_late_enrollment_and_carry_forward_skip_the_migration_item(self):
        student = create_student(school=self.school, student_id='STU-1')
        structure = FeeStructure.objects.create(
            school=self.school,
            term=self.term,
            created_by=self.user,
            status=FeeStructure.Status.DRAFT,
        )
        FeeItem.objects.create(
            fee_structure=structure,
            name='Tuition',
            amount=Decimal('100.00'),
            applies_to_type=FeeItem.AppliesToType.SCHOOL,
        )
        publish_fee_structure(structure)
        apply_fee_structure(structure)
        structure.refresh_from_db()
        FeeItem.objects.create(
            fee_structure=structure,
            name='Opening balance',
            amount=Decimal('0.00'),
            applies_to_type=FeeItem.AppliesToType.SCHOOL,
            is_migration_opening_balance=True,
        )
        create_class_enrollment(student=student, term=self.term, stream=self.stream)
        ensure_enrollment_fees(student.enrollments.get())
        self.assertEqual(
            list(StudentFee.objects.filter(student=student).values_list('name', 'amount')),
            [('Tuition', Decimal('100.00'))],
        )
        copied = carry_forward_fee_structure(
            school=self.school,
            term=self.second_term,
            created_by=self.user,
        )
        self.assertEqual(list(copied.fee_items.values_list('name', flat=True)), ['Tuition'])
        self.assertFalse(copied.fee_items.filter(is_migration_opening_balance=True).exists())
