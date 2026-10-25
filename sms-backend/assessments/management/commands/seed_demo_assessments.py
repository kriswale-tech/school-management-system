"""
Seed demo academics + fees across the active term and the previous two terms.

Uses an existing school's active-term enrollments / teaching assignments as the
template so the same students appear in prior terms with published scores,
approved/released results, applied fees, and a mix of payments.
"""

from __future__ import annotations

import random
from decimal import Decimal
from typing import Iterable

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import SchoolMembership, User
from assessments.models import (
    AssessmentItem,
    AssessmentItemScore,
    StudentResult,
    SubjectScore,
)
from assessments.services.class_overview import _required_teaching_assignments_for_student
from assessments.services.term_config import copy_forward_assessment_configs
from fees.models import FeeItem, FeeStructure, Payment, Receipt, StudentFee, StudentFeeCredit
from academics.models import ClassSubject
from fees.services.fees import apply_fee_structure, get_student_term_balance, publish_fee_structure
from schools.models import School, Term
from students.models import ClassEnrollment
from teachers.models import ClassTeacher, TeachingAssignment

CA_ITEMS = (
    ('Classwork 1', Decimal('20.00')),
    ('Classwork 2', Decimal('20.00')),
    ('Homework', Decimal('20.00')),
)

REMARKS = (
    'Good progress this term. Keep working hard.',
    'Shows consistent effort across subjects.',
    'Needs to participate more in class discussions.',
    'Excellent attitude and steady improvement.',
    'Capable student — encourage more revision at home.',
)

CONDUCT = ('Excellent', 'Very Good', 'Good', 'Satisfactory')
ATTITUDE = ('Positive', 'Cooperative', 'Improving', 'Attentive')
INTEREST = ('High', 'Steady', 'Growing', 'Fair')


class Command(BaseCommand):
    help = (
        'Seed published assessments, approved/released results, and fee payments '
        'for the active term plus the previous two terms (same students).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--school-id',
            type=str,
            help='School UUID. Defaults to the school with the most active-term enrollments.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print the plan without writing.',
        )
        parser.add_argument(
            '--reset-demo',
            action='store_true',
            help=(
                'Wipe prior-term demo structure (enrollments, teaching, scores, '
                'results, fees/payments) and re-seed. Active term keeps structure '
                'but refreshes missing scores/results/payments.'
            ),
        )
        parser.add_argument(
            '--seed',
            type=int,
            default=42,
            help='RNG seed for reproducible marks/payments (default: 42).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        reset_demo = options['reset_demo']
        rng = random.Random(options['seed'])

        school = self._resolve_school(options.get('school_id'))
        active = Term.objects.filter(school=school, is_active=True).select_related(
            'academic_year',
        ).first()
        if active is None:
            raise CommandError(f'{school.name} has no active term.')

        prior_terms = list(
            Term.objects.filter(school=school, start_date__lt=active.start_date)
            .select_related('academic_year')
            .order_by('-start_date')[:2]
        )
        prior_terms.reverse()  # chronological
        if len(prior_terms) < 2:
            raise CommandError(
                f'{school.name} needs at least two terms before the active term '
                f'({self._term_label(active)}). Found {len(prior_terms)}.'
            )

        template_enrollments = list(
            ClassEnrollment.objects.filter(term=active).select_related(
                'student',
                'stream',
                'class_level',
            )
        )
        if not template_enrollments:
            raise CommandError(
                f'{school.name} active term has no enrollments to clone.'
            )

        template_assignments = list(
            TeachingAssignment.objects.filter(term=active).select_related(
                'teacher',
                'class_subject',
                'stream',
                'subject_group',
            )
        )
        if not template_assignments:
            raise CommandError(
                f'{school.name} active term has no teaching assignments to clone.'
            )

        template_class_teachers = list(
            ClassTeacher.objects.filter(term=active).select_related(
                'teacher',
                'class_level',
                'stream',
            )
        )

        actor = self._resolve_actor(school)
        source_fee = (
            FeeStructure.objects.filter(school=school, term=active)
            .prefetch_related('fee_items')
            .first()
        )
        if source_fee is None or not source_fee.fee_items.exists():
            raise CommandError(
                f'{school.name} active term needs an applied fee structure with items '
                'to clone onto prior terms.'
            )

        target_terms = [*prior_terms, active]
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'{school.name} ({school.id})'
            f'{" [dry-run]" if dry_run else ""}'
            f'{" [reset-demo]" if reset_demo else ""}',
        ))
        self.stdout.write(
            f'  Active: {self._term_label(active)} | '
            f'Prior: {", ".join(self._term_label(t) for t in prior_terms)}',
        )
        self.stdout.write(
            f'  Template: {len(template_enrollments)} enrollments, '
            f'{len(template_assignments)} teaching assignments, '
            f'{len(template_class_teachers)} class teachers, '
            f'{source_fee.fee_items.count()} fee items.',
        )
        self.stdout.write(f'  Actor: {actor.get_full_name()} ({actor.email})')

        if dry_run:
            for term in target_terms:
                is_prior = term.id != active.id
                self.stdout.write(
                    f'  Would seed {self._term_label(term)}'
                    f'{" (clone structure from active)" if is_prior else " (fill gaps)"}'
                    f': academics + fees + payments',
                )
            self.stdout.write(self.style.SUCCESS('Dry-run complete. No changes written.'))
            return

        stats = {
            'enrollments': 0,
            'teaching': 0,
            'class_teachers': 0,
            'configs': 0,
            'ca_items': 0,
            'item_scores': 0,
            'subject_scores': 0,
            'results_released': 0,
            'fee_items': 0,
            'fee_applied': 0,
            'payments': 0,
            'reset': 0,
        }

        with transaction.atomic():
            if reset_demo:
                stats['reset'] = self._reset_prior_terms(prior_terms, school)

            default_teacher_id = template_assignments[0].teacher_id

            for term in prior_terms:
                stats['enrollments'] += self._ensure_enrollments(term, template_enrollments)
                stats['teaching'] += self._ensure_teaching(term, template_assignments)
                stats['class_teachers'] += self._ensure_class_teachers(
                    term,
                    template_class_teachers,
                )
                created_configs = copy_forward_assessment_configs(
                    school=school,
                    target_term=term,
                    source_term=active,
                )
                stats['configs'] += len(created_configs)

            for term in target_terms:
                stats['teaching'] += self._backfill_missing_teaching(
                    term,
                    default_teacher_id=default_teacher_id,
                )
                stats['class_teachers'] += self._backfill_missing_class_teachers(
                    term,
                    default_teacher_id=default_teacher_id,
                )
                ca, item_scores, subject_scores = self._seed_academics(term, rng)
                stats['ca_items'] += ca
                stats['item_scores'] += item_scores
                stats['subject_scores'] += subject_scores
                stats['results_released'] += self._approve_and_release(term, actor, rng)

            # Fees chronologically so payments land on the earliest outstanding term.
            for term in target_terms:
                fee_items, applied = self._ensure_fees(
                    school=school,
                    term=term,
                    source_fee=source_fee,
                    actor=actor,
                    is_active_term=term.id == active.id,
                )
                stats['fee_items'] += fee_items
                stats['fee_applied'] += applied
                stats['payments'] += self._seed_payments(
                    school=school,
                    term=term,
                    actor=actor,
                    rng=rng,
                )

        self.stdout.write(self.style.SUCCESS(
            'Seeded: '
            + ', '.join(f'{k}={v}' for k, v in stats.items() if v),
        ))

    def _resolve_school(self, school_id: str | None) -> School:
        if school_id:
            school = School.objects.filter(id=school_id).first()
            if school is None:
                raise CommandError(f'No school found with id {school_id}.')
            return school

        best = None
        best_count = -1
        for school in School.objects.all().order_by('name'):
            active = Term.objects.filter(school=school, is_active=True).first()
            if active is None:
                continue
            count = ClassEnrollment.objects.filter(term=active).count()
            if count > best_count:
                best = school
                best_count = count
        if best is None or best_count <= 0:
            raise CommandError('No school with an active term and enrollments found.')
        return best

    def _resolve_actor(self, school: School) -> User:
        membership = (
            SchoolMembership.objects.filter(
                school=school,
                is_active=True,
                role=User.RoleChoices.ADMIN,
            )
            .select_related('user')
            .first()
        )
        if membership is None:
            membership = (
                SchoolMembership.objects.filter(school=school, is_active=True)
                .select_related('user')
                .first()
            )
        if membership is None:
            raise CommandError(f'{school.name} has no active membership to act as.')
        return membership.user

    def _term_label(self, term: Term) -> str:
        return f'{term.academic_year.academic_year} {term.get_term_display()}'

    def _reset_prior_terms(self, prior_terms: list[Term], school: School) -> int:
        deleted = 0
        for term in prior_terms:
            deleted += AssessmentItemScore.objects.filter(
                assessment_item__teaching_assignment__term=term,
            ).delete()[0]
            deleted += SubjectScore.objects.filter(
                teaching_assignment__term=term,
            ).delete()[0]
            deleted += AssessmentItem.objects.filter(
                teaching_assignment__term=term,
            ).delete()[0]
            deleted += StudentResult.objects.filter(term=term).delete()[0]

            payment_ids = list(
                Payment.objects.filter(term=term, student__school=school).values_list(
                    'id',
                    flat=True,
                )
            )
            # Advance credits PROTECT source payments; wipe credits first.
            deleted += StudentFeeCredit.objects.filter(
                source_payment_id__in=payment_ids,
            ).delete()[0]
            deleted += Receipt.objects.filter(payment_id__in=payment_ids).delete()[0]
            deleted += Payment.objects.filter(id__in=payment_ids).delete()[0]
            deleted += StudentFee.objects.filter(term=term).delete()[0]

            structure = FeeStructure.objects.filter(school=school, term=term).first()
            if structure is not None:
                deleted += structure.fee_items.all().delete()[0]
                structure.status = FeeStructure.Status.DRAFT
                structure.published_at = None
                structure.applied_at = None
                structure.save(
                    update_fields=[
                        'status',
                        'published_at',
                        'applied_at',
                        'updated_at',
                    ],
                )

            deleted += TeachingAssignment.objects.filter(term=term).delete()[0]
            deleted += ClassTeacher.objects.filter(term=term).delete()[0]
            deleted += ClassEnrollment.objects.filter(term=term).delete()[0]
            self.stdout.write(f'  Reset {self._term_label(term)}')
        return deleted

    def _ensure_enrollments(
        self,
        term: Term,
        template: Iterable[ClassEnrollment],
    ) -> int:
        existing = set(
            ClassEnrollment.objects.filter(term=term).values_list('student_id', flat=True)
        )
        created = 0
        for row in template:
            if row.student_id in existing:
                continue
            ClassEnrollment.objects.create(
                student_id=row.student_id,
                term=term,
                class_level_id=row.class_level_id,
                stream_id=row.stream_id,
                is_new_student=False,
            )
            created += 1
        return created

    def _ensure_teaching(
        self,
        term: Term,
        template: Iterable[TeachingAssignment],
    ) -> int:
        created = 0
        for row in template:
            exists = TeachingAssignment.objects.filter(
                term=term,
                class_subject_id=row.class_subject_id,
                stream_id=row.stream_id,
                subject_group_id=row.subject_group_id,
            ).exists()
            if exists:
                continue
            TeachingAssignment.objects.create(
                teacher_id=row.teacher_id,
                class_subject_id=row.class_subject_id,
                stream_id=row.stream_id,
                subject_group_id=row.subject_group_id,
                term=term,
            )
            created += 1
        return created

    def _ensure_class_teachers(
        self,
        term: Term,
        template: Iterable[ClassTeacher],
    ) -> int:
        created = 0
        for row in template:
            qs = ClassTeacher.objects.filter(
                term=term,
                class_level_id=row.class_level_id,
            )
            if row.stream_id:
                qs = qs.filter(stream_id=row.stream_id)
            else:
                qs = qs.filter(stream__isnull=True)
            if qs.exists():
                continue
            ClassTeacher.objects.create(
                teacher_id=row.teacher_id,
                class_level_id=row.class_level_id,
                stream_id=row.stream_id,
                term=term,
            )
            created += 1
        return created

    def _backfill_missing_teaching(self, term: Term, *, default_teacher_id) -> int:
        """Create class-wide teaching assignments for enrolled classes missing subjects."""
        class_ids = set(
            ClassEnrollment.objects.filter(term=term).values_list(
                'class_level_id',
                flat=True,
            )
        )
        created = 0
        for class_level_id in class_ids:
            subjects = ClassSubject.objects.filter(
                class_level_id=class_level_id,
                is_active=True,
            )
            for class_subject in subjects:
                # Skip grouped subjects — placement is required; leave those alone.
                if class_subject.groups.filter(is_active=True).exists():
                    continue
                exists = TeachingAssignment.objects.filter(
                    term=term,
                    class_subject=class_subject,
                    stream__isnull=True,
                    subject_group__isnull=True,
                ).exists()
                if exists:
                    continue
                # Prefer an existing teacher already on this class/term.
                existing_teacher = (
                    TeachingAssignment.objects.filter(
                        term=term,
                        class_subject__class_level_id=class_level_id,
                    )
                    .values_list('teacher_id', flat=True)
                    .first()
                )
                TeachingAssignment.objects.create(
                    teacher_id=existing_teacher or default_teacher_id,
                    class_subject=class_subject,
                    term=term,
                )
                created += 1
        return created

    def _backfill_missing_class_teachers(self, term: Term, *, default_teacher_id) -> int:
        """Ensure every enrolled stream has a class teacher for approval workflows."""
        created = 0
        pairs = (
            ClassEnrollment.objects.filter(term=term)
            .values_list('class_level_id', 'stream_id')
            .distinct()
        )
        for class_level_id, stream_id in pairs:
            qs = ClassTeacher.objects.filter(term=term, class_level_id=class_level_id)
            if stream_id:
                qs = qs.filter(stream_id=stream_id)
            else:
                qs = qs.filter(stream__isnull=True)
            if qs.exists():
                continue
            teacher_id = (
                TeachingAssignment.objects.filter(
                    term=term,
                    class_subject__class_level_id=class_level_id,
                )
                .values_list('teacher_id', flat=True)
                .first()
            ) or default_teacher_id
            ClassTeacher.objects.create(
                teacher_id=teacher_id,
                class_level_id=class_level_id,
                stream_id=stream_id,
                term=term,
            )
            created += 1
        return created

    def _roster_student_ids(self, assignment: TeachingAssignment) -> list:
        from academics.models import StudentSubjectGroup

        qs = ClassEnrollment.objects.filter(
            term=assignment.term,
            class_level_id=assignment.class_subject.class_level_id,
        )
        if assignment.stream_id:
            qs = qs.filter(stream_id=assignment.stream_id)
        if assignment.subject_group_id:
            group_ids = StudentSubjectGroup.objects.filter(
                academic_year_id=assignment.term.academic_year_id,
                subject_group_id=assignment.subject_group_id,
            ).values_list('student_id', flat=True)
            qs = qs.filter(student_id__in=group_ids)
        return list(qs.values_list('student_id', flat=True))

    def _ensure_ca_items(self, assignment: TeachingAssignment) -> int:
        created = 0
        existing = {
            name.casefold()
            for name in AssessmentItem.objects.filter(
                teaching_assignment=assignment,
            ).values_list('name', flat=True)
        }
        order = (
            AssessmentItem.objects.filter(teaching_assignment=assignment).count() or 0
        )
        for name, max_marks in CA_ITEMS:
            if name.casefold() in existing:
                continue
            order += 1
            AssessmentItem.objects.create(
                teaching_assignment=assignment,
                name=name,
                max_marks=max_marks,
                order=order,
            )
            created += 1
        return created

    def _seed_academics(self, term: Term, rng: random.Random) -> tuple[int, int, int]:
        ca_created = 0
        item_scores = 0
        subject_scores = 0
        now = timezone.now()

        assignments = list(
            TeachingAssignment.objects.filter(term=term).select_related(
                'class_subject',
                'term__academic_year',
            )
        )
        for assignment in assignments:
            ca_created += self._ensure_ca_items(assignment)
            items = list(AssessmentItem.objects.filter(teaching_assignment=assignment))
            if not items:
                continue
            student_ids = self._roster_student_ids(assignment)
            for student_id in student_ids:
                for item in items:
                    _, was_created = AssessmentItemScore.objects.get_or_create(
                        assessment_item=item,
                        student_id=student_id,
                        defaults={
                            'mark': self._random_mark(rng, item.max_marks),
                        },
                    )
                    if was_created:
                        item_scores += 1

                score, created = SubjectScore.objects.get_or_create(
                    teaching_assignment=assignment,
                    student_id=student_id,
                    defaults={
                        'exam_mark': self._random_mark(rng, Decimal('100.00')),
                        'is_published': True,
                        'published_at': now,
                    },
                )
                if created:
                    subject_scores += 1
                elif not score.is_published or score.exam_mark is None:
                    score.exam_mark = score.exam_mark or self._random_mark(
                        rng,
                        Decimal('100.00'),
                    )
                    score.is_published = True
                    score.published_at = score.published_at or now
                    score.save(
                        update_fields=[
                            'exam_mark',
                            'is_published',
                            'published_at',
                            'updated_at',
                        ],
                    )
                    subject_scores += 1

        return ca_created, item_scores, subject_scores

    def _random_mark(self, rng: random.Random, max_marks: Decimal) -> Decimal:
        # Bias toward mid/high scores so reports look realistic.
        ratio = rng.uniform(0.45, 0.98)
        value = (Decimal(str(round(ratio, 4))) * max_marks).quantize(Decimal('0.01'))
        if value > max_marks:
            value = max_marks
        if value < 0:
            value = Decimal('0.00')
        return value

    def _approve_and_release(
        self,
        term: Term,
        actor: User,
        rng: random.Random,
    ) -> int:
        """Approve + release every enrolled student whose required subjects are published."""
        released = 0
        now = timezone.now()
        enrollments = ClassEnrollment.objects.filter(term=term).select_related(
            'stream',
            'class_level',
        )
        for enrollment in enrollments:
            required = _required_teaching_assignments_for_student(
                student_id=enrollment.student_id,
                class_level_id=enrollment.class_level_id,
                term=term,
                stream_id=enrollment.stream_id,
            )
            if not required:
                continue
            if not all(
                SubjectScore.objects.filter(
                    teaching_assignment=assignment,
                    student_id=enrollment.student_id,
                    is_published=True,
                ).exists()
                for assignment in required
            ):
                continue

            existing = StudentResult.objects.filter(
                student_id=enrollment.student_id,
                term=term,
                class_level_id=enrollment.class_level_id,
                stream_id=enrollment.stream_id,
            ).first()
            if existing and existing.status == StudentResult.Status.RELEASED:
                continue

            StudentResult.objects.update_or_create(
                student_id=enrollment.student_id,
                term=term,
                class_level_id=enrollment.class_level_id,
                stream_id=enrollment.stream_id,
                defaults={
                    'status': StudentResult.Status.RELEASED,
                    'remarks': rng.choice(REMARKS),
                    'conduct': rng.choice(CONDUCT),
                    'attitude': rng.choice(ATTITUDE),
                    'interest': rng.choice(INTEREST),
                    'head_teacher_remarks': 'Released for parent collection.',
                    'approved_at': now,
                    'approved_by': actor,
                    'released_at': now,
                    'released_by': actor,
                },
            )
            released += 1
        return released

    def _ensure_fees(
        self,
        *,
        school: School,
        term: Term,
        source_fee: FeeStructure,
        actor: User,
        is_active_term: bool,
    ) -> tuple[int, int]:
        structure = FeeStructure.objects.filter(school=school, term=term).first()
        if structure is None:
            structure = FeeStructure.objects.create(
                school=school,
                term=term,
                created_by=actor,
            )

        items_created = 0
        if not structure.fee_items.exists():
            for item in source_fee.fee_items.all():
                FeeItem.objects.create(
                    fee_structure=structure,
                    name=item.name,
                    amount=item.amount,
                    description=item.description,
                    applies_to_type=item.applies_to_type,
                    applies_to_id=item.applies_to_id,
                    student_type=item.student_type,
                )
                items_created += 1

        applied = 0
        if structure.status != FeeStructure.Status.APPLIED:
            if structure.status == FeeStructure.Status.DRAFT:
                publish_fee_structure(structure)
                structure.refresh_from_db()
            apply_fee_structure(structure)
            structure.refresh_from_db()
            applied = 1
        elif not is_active_term:
            # Already applied — nothing to do.
            pass

        return items_created, applied

    def _seed_payments(
        self,
        *,
        school: School,
        term: Term,
        actor: User,
        rng: random.Random,
    ) -> int:
        """Record a mix of full / partial / skipped payments on this term."""
        from students.models import Student

        created = 0
        student_ids = list(
            ClassEnrollment.objects.filter(term=term).values_list('student_id', flat=True)
        )
        rng.shuffle(student_ids)
        # Unique demo receipt numbers avoid collisions with the live RCPT-* sequence
        # (count-based generation breaks when numbers have gaps after deletes).
        stamp = timezone.now().strftime('%Y%m%d%H%M%S')

        for index, student_id in enumerate(student_ids):
            student = Student.objects.get(id=student_id)
            balance = get_student_term_balance(student=student, term=term)
            owing = balance['balance']
            if owing <= 0:
                continue

            # ~55% full, ~25% partial, ~20% unpaid for this pass.
            roll = rng.random()
            if roll < 0.20:
                continue
            if roll < 0.45:
                amount = (owing * Decimal(str(round(rng.uniform(0.35, 0.75), 2)))).quantize(
                    Decimal('0.01'),
                )
                if amount <= 0:
                    continue
            else:
                amount = owing

            payment = Payment.objects.create(
                student=student,
                term=term,
                amount=amount,
                payment_method=rng.choice([
                    Payment.PaymentMethod.CASH,
                    Payment.PaymentMethod.MOBILE_MONEY,
                    Payment.PaymentMethod.BANK_TRANSFER,
                ]),
                paid_at=timezone.now(),
                recorded_by=actor,
                payment_reference=f'DEMO-{term.term}-{index + 1}',
                payment_notes='Demo seed payment',
            )
            Receipt.objects.create(
                payment=payment,
                receipt_number=f'DEMO-{stamp}-{term.term}-{index + 1:04d}',
                issued_by=actor,
            )
            created += 1
        return created
