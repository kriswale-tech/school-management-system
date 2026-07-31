from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from academics.models import ClassLevel, Level
from accounts.tests.factories import create_user, user_school
from fees.models import FeeItem, FeeStructure, Payment, StudentFee
from fees.services import (
    apply_fee_structure,
    carry_forward_fee_structure,
    get_student_term_balance,
    publish_fee_structure,
)
from schools.models import AcademicYear, Term
from students.tests.factories import create_student, enroll_student


class FeeStructureTests(TestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        self.school = user_school(self.user)
        self.academic_year = AcademicYear.objects.create(
            school=self.school,
            academic_year='2025/2026',
            start_date='2025-09-01',
            end_date='2026-07-31',
            is_active=True,
        )
        self.first_term = Term.objects.create(
            school=self.school,
            academic_year=self.academic_year,
            term=Term.TermChoices.FIRST_TERM,
            start_date='2025-09-01',
            end_date='2025-12-15',
            is_active=True,
        )
        self.second_term = Term.objects.create(
            school=self.school,
            academic_year=self.academic_year,
            term=Term.TermChoices.SECOND_TERM,
            start_date='2025-12-16',
            end_date='2026-04-01',
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
        self.student = create_student(
            school=self.school,
            student_id='STU-100',
            first_name='Ama',
            last_name='Mensah',
        )
        enroll_student(
            student=self.student,
            term=self.first_term,
            class_level=self.class_level,
            is_new_student=True,
        )

    def _create_structure_with_item(self, *, term=None, amount=Decimal('500.00')):
        structure = FeeStructure.objects.create(
            school=self.school,
            term=term or self.first_term,
            created_by=self.user,
        )
        FeeItem.objects.create(
            fee_structure=structure,
            name='Tuition Fee',
            amount=amount,
            applies_to_type=FeeItem.AppliesToType.SCHOOL,
            student_type=FeeItem.StudentType.ALL_STUDENTS,
        )
        return structure

    def test_publish_and_apply_create_student_fees(self):
        structure = self._create_structure_with_item()
        publish_fee_structure(structure)
        apply_fee_structure(structure)

        structure.refresh_from_db()
        self.assertEqual(structure.status, FeeStructure.Status.APPLIED)
        self.assertEqual(StudentFee.objects.filter(student=self.student).count(), 1)
        self.assertEqual(
            StudentFee.objects.get(student=self.student).amount,
            Decimal('500.00'),
        )

    def test_locked_structure_rejects_fee_item_changes(self):
        structure = self._create_structure_with_item()
        publish_fee_structure(structure)
        apply_fee_structure(structure)

        with self.assertRaises(ValidationError):
            FeeItem.objects.create(
                fee_structure=structure,
                name='Extra Fee',
                amount=Decimal('50.00'),
                applies_to_type=FeeItem.AppliesToType.SCHOOL,
            )

    def test_carry_forward_copies_previous_term_items(self):
        first_structure = self._create_structure_with_item(amount=Decimal('300.00'))
        publish_fee_structure(first_structure)
        apply_fee_structure(first_structure)

        second_structure = carry_forward_fee_structure(
            school=self.school,
            term=self.second_term,
            created_by=self.user,
        )

        self.assertEqual(second_structure.status, FeeStructure.Status.CARRIED_FORWARD)
        self.assertEqual(second_structure.fee_items.count(), 1)
        self.assertEqual(second_structure.fee_items.get().amount, Decimal('300.00'))

    def test_student_term_balance_shows_running_balance(self):
        structure = self._create_structure_with_item(amount=Decimal('1000.00'))
        publish_fee_structure(structure)
        apply_fee_structure(structure)

        Payment.objects.create(
            student=self.student,
            term=self.first_term,
            amount=Decimal('400.00'),
            payment_method=Payment.PaymentMethod.CASH,
            paid_at=timezone.now(),
            recorded_by=self.user,
        )

        balance = get_student_term_balance(student=self.student, term=self.first_term)

        self.assertEqual(balance['total_billed'], Decimal('1000.00'))
        self.assertEqual(balance['total_paid'], Decimal('400.00'))
        self.assertEqual(balance['balance'], Decimal('600.00'))
        self.assertEqual(balance['payment_status'], 'partially_paid')
        self.assertEqual(len(balance['fee_items']), 1)
        self.assertEqual(len(balance['payments']), 1)

    def test_new_student_fee_item_only_applies_to_new_students(self):
        continuing_student = create_student(
            school=self.school,
            student_id='STU-101',
            first_name='Kofi',
            last_name='Boateng',
        )
        enroll_student(
            student=continuing_student,
            term=self.first_term,
            class_level=self.class_level,
            is_new_student=False,
        )

        structure = FeeStructure.objects.create(
            school=self.school,
            term=self.first_term,
            created_by=self.user,
        )
        FeeItem.objects.create(
            fee_structure=structure,
            name='Admission Fee',
            amount=Decimal('150.00'),
            applies_to_type=FeeItem.AppliesToType.SCHOOL,
            student_type=FeeItem.StudentType.NEW_STUDENT,
        )
        publish_fee_structure(structure)
        apply_fee_structure(structure)

        self.assertEqual(StudentFee.objects.filter(student=self.student).count(), 1)
        self.assertEqual(StudentFee.objects.filter(student=continuing_student).count(), 0)
