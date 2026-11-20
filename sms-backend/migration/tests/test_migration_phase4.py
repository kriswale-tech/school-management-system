from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import load_workbook
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, Level
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from fees.models import FeeItem, FeeStructure, Payment, PaymentAllocation, Receipt, StudentFee, StudentFeeCredit
from fees.services.credits import apply_available_credits_for_student
from fees.services.fees import apply_fee_structure, get_student_term_balance, list_student_payments, publish_fee_structure
from migration.models import MigrationFile, MigrationHistoricalCharge, MigrationHistoricalPayment, MigrationJob
from migration.services.historical_commit import process_historical_commit
from schools.models import AcademicYear, Term
from students.services import create_class_enrollment
from students.tests.factories import create_student, ensure_default_stream


CHARGES = (
    'Student ID,Academic year,Term,Fee item,Amount\n'
    'STU-1,2024/2025,first,Tuition,500.00\n'
    'STU-1,2024/2025,first,Books,200.00\n'
    'STU-1,2024/2025,second,Tuition,500.00\n'
)
PAYMENTS = (
    'Student ID,Payment reference,Payment date,Amount,Payment method,Academic year,Term,Receipt number,Payment type\n'
    'STU-1,PAY-1,2020-01-15,700.00,cash,2024/2025,first,,ordinary\n'
    'STU-1,PAY-2,2020-05-10,200.00,cash,2024/2025,second,,ordinary\n'
    'STU-1,PAY-3,2020-09-01,300.00,cash,2024/2025,second,R-9,advance\n'
)


class HistoricalFinanceMigrationTests(APITestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        set_client_auth_cookies(self.client, self.user)
        self.school = user_school(self.user)
        self.year = AcademicYear.objects.create(
            school=self.school,
            academic_year='2024/2025',
            start_date='2024-09-01',
            end_date='2025-07-31',
            is_active=True,
        )
        self.first = Term.objects.create(
            school=self.school,
            academic_year=self.year,
            term=Term.TermChoices.FIRST_TERM,
            start_date='2024-09-01',
            end_date='2024-12-15',
            is_active=True,
        )
        self.second = Term.objects.create(
            school=self.school,
            academic_year=self.year,
            term=Term.TermChoices.SECOND_TERM,
            start_date='2024-12-16',
            end_date='2025-03-31',
            is_active=False,
        )
        self.third = Term.objects.create(
            school=self.school,
            academic_year=self.year,
            term=Term.TermChoices.THIRD_TERM,
            start_date='2025-04-01',
            end_date='2025-07-31',
            is_active=False,
        )
        self.student = create_student(school=self.school, student_id='STU-1')

    def start(self):
        created = self.client.post(
            reverse('migration-job-list'),
            {
                'job_type': 'fee_financial_history',
                'template': 'historical_finance',
                'source_system': 'Legacy',
            },
            format='json',
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        return created.data['id']

    def upload(self, job_id, name, content, role):
        uploaded = self.client.post(
            reverse('migration-job-upload', kwargs={'job_id': job_id}),
            {
                'file': SimpleUploadedFile(name, content.encode(), content_type='text/csv'),
                'role': role,
            },
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
        return uploaded.data

    def validate(self, job_id):
        checked = self.client.post(reverse('migration-job-validate', kwargs={'job_id': job_id}))
        self.assertEqual(checked.status_code, status.HTTP_200_OK, checked.data)
        preview = self.client.get(reverse('migration-job-plan', kwargs={'job_id': job_id}))
        self.assertEqual(preview.status_code, status.HTTP_200_OK, preview.data)
        return preview.data

    def commit(self, job_id):
        return self.client.post(
            reverse('migration-job-commit', kwargs={'job_id': job_id}),
            {'confirm': True},
            format='json',
        )

    def test_templates_list_the_charge_and_payment_columns(self):
        charges = self.client.get(reverse('migration-template', kwargs={'template': 'historical_charges'}))
        payments = self.client.get(reverse('migration-template', kwargs={'template': 'historical_payments'}))
        self.assertEqual(charges.status_code, status.HTTP_200_OK)
        workbook = load_workbook(BytesIO(charges.content))
        self.assertEqual(
            [cell.value for cell in workbook['Charges'][1]],
            ['Student ID', 'Academic year', 'Term', 'Fee item', 'Amount', 'Source reference', 'Notes'],
        )
        payment_book = load_workbook(BytesIO(payments.content))
        self.assertEqual(
            [cell.value for cell in payment_book['Payments'][1]],
            [
                'Student ID',
                'Payment reference',
                'Payment date',
                'Amount',
                'Payment method',
                'Academic year',
                'Term',
                'Receipt number',
                'Payment type',
                'Notes',
            ],
        )

    def test_charges_and_payments_rebuild_the_term_balance(self):
        job_id = self.start()
        self.upload(job_id, 'charges.csv', CHARGES, 'charges')
        self.upload(job_id, 'payments.csv', PAYMENTS, 'payments')
        preview = self.validate(job_id)
        self.assertEqual(preview['summary']['history']['charge_total'], '1200.00')
        self.assertEqual(preview['summary']['history']['payment_total'], '900.00')
        self.assertEqual(preview['summary']['history']['advance_total'], '300.00')
        saved = self.commit(job_id)
        self.assertEqual(saved.status_code, status.HTTP_200_OK, saved.data)
        self.assertEqual(saved.data['status'], 'committed')
        self.assertEqual(StudentFee.objects.filter(student=self.student).count(), 3)
        self.assertEqual(Payment.objects.filter(student=self.student).count(), 3)
        self.assertEqual(Receipt.objects.count(), 0)
        first = get_student_term_balance(student=self.student, term=self.first)
        second = get_student_term_balance(student=self.student, term=self.second)
        self.assertEqual(first['balance'], Decimal('0.00'))
        self.assertEqual(second['balance'], Decimal('300.00'))
        pay1 = Payment.objects.get(payment_reference='PAY-1')
        self.assertEqual(pay1.amount, Decimal('700.00'))
        self.assertEqual(pay1.allocations.count(), 1)
        advance = StudentFeeCredit.objects.get(student=self.student)
        self.assertTrue(advance.is_migration_hold)
        self.assertEqual(advance.remaining_amount, Decimal('300.00'))
        history = list_student_payments(school=self.school, student=self.student, term_id=self.second.id)
        receipts = {row['legacy_receipt_number'] for row in history}
        self.assertIn('R-9', receipts)
        self.assertTrue(any(row['is_advance'] for row in history))
        apply_available_credits_for_student(
            student=self.student,
            term=self.second,
            recorded_by=self.user,
            school=self.school,
        )
        advance.refresh_from_db()
        self.assertEqual(advance.remaining_amount, Decimal('300.00'))
        self.assertFalse(Payment.objects.filter(payment_method=Payment.PaymentMethod.ADVANCE_CREDIT).exists())
        process_historical_commit(job_id)
        self.assertEqual(StudentFee.objects.count(), 3)
        self.assertEqual(Payment.objects.count(), 3)

    def test_one_reference_across_two_terms_is_one_payment(self):
        job_id = self.start()
        self.upload(
            job_id,
            'charges.csv',
            'Student ID,Academic year,Term,Fee item,Amount\n'
            'STU-1,2024/2025,first,Tuition,400.00\n'
            'STU-1,2024/2025,second,Tuition,100.00\n',
            'charges',
        )
        self.upload(
            job_id,
            'payments.csv',
            'Student ID,Payment reference,Payment date,Amount,Payment method,Academic year,Term,Receipt number,Payment type\n'
            'STU-1,PAY-9,2020-01-15,400.00,cash,2024/2025,first,R-1,ordinary\n'
            'STU-1,PAY-9,2020-01-15,100.00,cash,2024/2025,second,R-1,ordinary\n',
            'payments',
        )
        self.validate(job_id)
        saved = self.commit(job_id)
        self.assertEqual(saved.status_code, status.HTTP_200_OK, saved.data)
        payment = Payment.objects.get()
        self.assertEqual(payment.amount, Decimal('500.00'))
        self.assertEqual(payment.legacy_receipt_number, 'R-1')
        self.assertEqual(PaymentAllocation.objects.filter(payment=payment).count(), 2)
        self.assertEqual(MigrationHistoricalPayment.objects.count(), 1)

    def test_a_repeated_fee_and_a_conflicting_payment_are_left_out(self):
        job_id = self.start()
        self.upload(
            job_id,
            'charges.csv',
            'Student ID,Academic year,Term,Fee item,Amount\n'
            'STU-1,2024/2025,first,Tuition,100.00\n'
            'STU-1,2024/2025,first,Tuition,50.00\n',
            'charges',
        )
        self.upload(
            job_id,
            'payments.csv',
            'Student ID,Payment reference,Payment date,Amount,Payment method,Academic year,Term,Receipt number,Payment type\n'
            'STU-1,PAY-1,2020-01-15,40.00,cash,2024/2025,first,,ordinary\n'
            'STU-1,PAY-1,2020-02-01,40.00,cash,2024/2025,second,,ordinary\n',
            'payments',
        )
        preview = self.validate(job_id)
        self.assertEqual(preview['summary']['history']['valid_rows'], 0)
        self.assertGreaterEqual(preview['summary']['history']['blocked_rows'], 4)
        saved = self.commit(job_id)
        self.assertEqual(saved.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(StudentFee.objects.count(), 0)

    def test_an_opening_balance_blocks_that_term_only(self):
        structure = FeeStructure.objects.create(
            school=self.school,
            term=self.third,
            created_by=self.user,
            status=FeeStructure.Status.DRAFT,
        )
        item = FeeItem.objects.create(
            fee_structure=structure,
            name='Opening balance',
            amount=Decimal('0.00'),
            applies_to_type=FeeItem.AppliesToType.SCHOOL,
            is_migration_opening_balance=True,
        )
        fee = StudentFee.objects.create(
            student=self.student,
            term=self.third,
            fee_structure=structure,
            fee_item=item,
            name='Opening balance',
            amount=Decimal('400.00'),
        )
        from migration.models import MigrationOpeningBalance
        MigrationOpeningBalance.objects.create(
            school=self.school,
            job=MigrationJob.objects.create(
                school=self.school,
                job_type=MigrationJob.JobType.FEE_FINANCIAL_HISTORY,
                template=MigrationJob.Template.OPENING_BALANCES,
                created_by=self.user,
            ),
            student=self.student,
            term=self.third,
            student_fee=fee,
            source_row_number=1,
            amount=Decimal('400.00'),
        )
        job_id = self.start()
        self.upload(
            job_id,
            'charges.csv',
            'Student ID,Academic year,Term,Fee item,Amount\n'
            'STU-1,2024/2025,first,Tuition,80.00\n'
            'STU-1,2024/2025,third,Tuition,80.00\n',
            'charges',
        )
        preview = self.validate(job_id)
        self.assertEqual(preview['summary']['history']['valid_rows'], 1)
        self.assertEqual(preview['summary']['history']['blocked_rows'], 1)
        saved = self.commit(job_id)
        self.assertEqual(saved.status_code, status.HTTP_200_OK, saved.data)
        self.assertEqual(StudentFee.objects.filter(fee_item__is_migration_historical=True).count(), 1)
        self.assertEqual(fee.amount, Decimal('400.00'))

    def test_a_second_import_does_not_duplicate_a_payment_reference(self):
        job_id = self.start()
        self.upload(
            job_id,
            'charges.csv',
            'Student ID,Academic year,Term,Fee item,Amount\nSTU-1,2024/2025,first,Tuition,50.00\n',
            'charges',
        )
        self.upload(
            job_id,
            'payments.csv',
            'Student ID,Payment reference,Payment date,Amount,Payment method,Academic year,Term,Receipt number,Payment type\n'
            'STU-1,PAY-1,2020-01-15,50.00,cash,2024/2025,first,,ordinary\n',
            'payments',
        )
        self.validate(job_id)
        self.assertEqual(self.commit(job_id).status_code, status.HTTP_200_OK)
        again = self.start()
        self.upload(
            again,
            'charges.csv',
            'Student ID,Academic year,Term,Fee item,Amount\nSTU-1,2024/2025,first,Books,10.00\n',
            'charges',
        )
        self.upload(
            again,
            'payments.csv',
            'Student ID,Payment reference,Payment date,Amount,Payment method,Academic year,Term,Receipt number,Payment type\n'
            'STU-1,PAY-1,2020-01-15,50.00,cash,2024/2025,first,,ordinary\n',
            'payments',
        )
        preview = self.validate(again)
        self.assertEqual(preview['summary']['history']['blocked_rows'], 1)
        self.assertEqual(preview['summary']['history']['valid_rows'], 1)
        self.assertEqual(self.commit(again).status_code, status.HTTP_200_OK)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(MigrationHistoricalCharge.objects.count(), 2)

    def test_replacing_the_charges_file_keeps_the_payments_file(self):
        job_id = self.start()
        self.upload(job_id, 'charges.csv', CHARGES, 'charges')
        self.upload(job_id, 'payments.csv', PAYMENTS, 'payments')
        self.upload(
            job_id,
            'charges-again.csv',
            'Student ID,Academic year,Term,Fee item,Amount\nSTU-1,2024/2025,first,Tuition,10.00\n',
            'charges',
        )
        names = set(MigrationFile.objects.filter(job_id=job_id).values_list('original_filename', 'role'))
        self.assertEqual(names, {('charges-again.csv', 'charges'), ('payments.csv', 'payments')})

    def test_historical_fee_items_stay_out_of_fee_application(self):
        job_id = self.start()
        self.upload(
            job_id,
            'charges.csv',
            'Student ID,Academic year,Term,Fee item,Amount\nSTU-1,2024/2025,first,Old tuition,25.00\n',
            'charges',
        )
        self.validate(job_id)
        self.assertEqual(self.commit(job_id).status_code, status.HTTP_200_OK)
        structure = FeeStructure.objects.get(school=self.school, term=self.first)
        FeeItem.objects.create(
            fee_structure=structure,
            name='Tuition',
            amount=Decimal('100.00'),
            applies_to_type=FeeItem.AppliesToType.SCHOOL,
        )
        level = Level.objects.create(school=self.school, name='Junior High', is_system_generated=False)
        class_level = ClassLevel.objects.create(
            school=self.school,
            level=level,
            name='JHS 1',
            is_system_generated=False,
        )
        create_class_enrollment(
            student=self.student,
            term=self.first,
            stream=ensure_default_stream(class_level),
        )
        publish_fee_structure(structure)
        apply_fee_structure(structure)
        names = set(StudentFee.objects.filter(student=self.student).values_list('name', flat=True))
        self.assertEqual(names, {'Old tuition', 'Tuition'})
        self.assertEqual(
            StudentFee.objects.filter(student=self.student, fee_item__is_migration_historical=True).count(),
            1,
        )
