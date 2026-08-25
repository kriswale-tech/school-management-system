from datetime import date
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from academics.models import ClassLevel, Level
from accounts.tests.factories import create_user, user_school
from fees.models import FeeItem, FeeStructure, Payment, StudentFeeCredit
from fees.services import apply_fee_structure, publish_fee_structure
from fees.services.backfill_advances import (
    backfill_advances_for_school,
    reconcile_duplicate_backfill_credits_for_school,
)
from fees.services.credits import create_credit_from_excess
from schools.models import AcademicYear, Term
from students.tests.factories import create_student, enroll_student, ensure_default_stream


class BackfillFeeAdvancesTests(TestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
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
        self.level = Level.objects.create(
            school=self.school,
            name='Junior High',
            is_system_generated=False,
        )
        self.class_level = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='JHS 1',
            is_system_generated=False,
        )
        self.stream = ensure_default_stream(self.class_level)
        self.student = create_student(
            school=self.school,
            student_id='TA-0099',
            first_name='Yaw',
            last_name='Boateng',
        )
        enroll_student(
            student=self.student,
            term=self.term,
            stream=self.stream,
            is_new_student=True,
        )

        structure = FeeStructure.objects.create(
            school=self.school,
            term=self.term,
            created_by=self.user,
        )
        FeeItem.objects.create(
            fee_structure=structure,
            name='Tuition Fee',
            amount=Decimal('1500.00'),
            applies_to_type=FeeItem.AppliesToType.SCHOOL,
            student_type=FeeItem.StudentType.ALL_STUDENTS,
        )
        publish_fee_structure(structure)
        apply_fee_structure(structure)

        self.payment = Payment.objects.create(
            student=self.student,
            term=self.term,
            amount=Decimal('1700.00'),
            payment_method=Payment.PaymentMethod.CASH,
            recorded_by=self.user,
            paid_at=timezone.now(),
        )

    def test_backfill_creates_advance_for_excess(self):
        result = backfill_advances_for_school(school=self.school, dry_run=False)
        self.assertEqual(len(result['created']), 1)
        self.assertEqual(result['created'][0]['uncovered'], Decimal('200.00'))

        credit = StudentFeeCredit.objects.get(student=self.student)
        self.assertEqual(credit.remaining_amount, Decimal('200.00'))
        self.assertEqual(credit.status, StudentFeeCredit.Status.AVAILABLE)

        second = backfill_advances_for_school(school=self.school, dry_run=False)
        self.assertEqual(len(second['created']), 0)
        self.assertEqual(len(second['skipped']), 1)
        self.assertEqual(second['skipped'][0]['reason'], 'already_covered')
        self.assertEqual(StudentFeeCredit.objects.filter(student=self.student).count(), 1)

    def test_skips_when_live_advance_already_covers_excess(self):
        create_credit_from_excess(
            school=self.school,
            student=self.student,
            amount=Decimal('200.00'),
            source_payment=self.payment,
        )

        result = backfill_advances_for_school(school=self.school, dry_run=False)
        self.assertEqual(len(result['created']), 0)
        self.assertEqual(len(result['skipped']), 1)
        self.assertEqual(result['skipped'][0]['reason'], 'already_covered')
        self.assertEqual(StudentFeeCredit.objects.filter(student=self.student).count(), 1)

    def test_reconcile_removes_duplicate_backfill(self):
        live = create_credit_from_excess(
            school=self.school,
            student=self.student,
            amount=Decimal('200.00'),
            source_payment=self.payment,
        )
        duplicate = create_credit_from_excess(
            school=self.school,
            student=self.student,
            amount=Decimal('200.00'),
            source_payment=self.payment,
        )
        duplicate.notes = (
            'Backfilled from historical overpayment '
            f'(1700.00 paid vs 1500.00 billed for term {self.term.id}).'
        )
        duplicate.save(update_fields=['notes', 'updated_at'])

        removed = reconcile_duplicate_backfill_credits_for_school(
            school=self.school,
            dry_run=False,
        )
        self.assertEqual(len(removed), 1)
        self.assertEqual(removed[0]['credit_id'], str(duplicate.id))
        self.assertTrue(StudentFeeCredit.objects.filter(id=live.id).exists())
        self.assertFalse(StudentFeeCredit.objects.filter(id=duplicate.id).exists())

    def test_management_command_runs(self):
        out = StringIO()
        call_command('backfill_fee_advances', stdout=out)
        self.assertIn('Created 1 advance credit', out.getvalue())
        self.assertTrue(StudentFeeCredit.objects.filter(student=self.student).exists())
