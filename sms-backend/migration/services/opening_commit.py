"""Write opening balances as StudentFee charges. No payments, credits, or notices."""

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from fees.models import FeeItem, FeeStructure, StudentFee
from migration.models import (
    MigrationCommitRecord,
    MigrationJob,
    MigrationOpeningBalance,
    MigrationRow,
)
from migration.services.audit import record_migration_audit
from migration.services.ingest import release_stored_file
from migration.services.opening_plan import plan_opening_job, resolved_term
from migration.services.student_commit import _ensure_historical_years
from students.models import Student

BATCH_SIZE = 200


def begin_opening_commit(*, job, actor, confirmed_total):
    if job.template != MigrationJob.Template.OPENING_BALANCES:
        raise ValidationError({'job': 'This commit is only for opening balances.'})
    if job.job_type != MigrationJob.JobType.FEE_FINANCIAL_HISTORY:
        raise ValidationError({'job': 'Opening balances use the fee import.'})
    if job.status in {MigrationJob.Status.COMMITTED, MigrationJob.Status.CANCELLED, MigrationJob.Status.ABANDONED}:
        raise ValidationError({'job': 'This migration is already finished.'})
    summary = plan_opening_job(job)
    expected = Decimal(summary['opening']['total'])
    try:
        given = Decimal(str(confirmed_total)).quantize(Decimal('0.01'))
    except (InvalidOperation, TypeError):
        raise ValidationError({'confirmed_total': f'Confirm the total of GHS {expected:.2f}.'}) from None
    if given != expected:
        raise ValidationError({'confirmed_total': f'Confirm the total of GHS {expected:.2f}.'})
    with transaction.atomic():
        competing = (
            MigrationJob.objects.select_for_update()
            .filter(
                school=job.school,
                status__in=[MigrationJob.Status.COMMITTING, MigrationJob.Status.PARTIALLY_COMMITTED],
            )
            .exclude(pk=job.pk)
        )
        if competing.exists():
            raise ValidationError({'job': 'Another migration is still committing for this school.'})
        job.status = MigrationJob.Status.COMMITTING
        job.committed_by = actor
        job.heartbeat_at = timezone.now()
        job.save(update_fields=['status', 'committed_by', 'heartbeat_at', 'updated_at'])
    record_migration_audit(
        school=job.school,
        job=job,
        actor=actor,
        action='commit',
        summary=f'Confirmed opening balances of GHS {expected:.2f}.',
        payload={'total': f'{expected:.2f}', 'valid_rows': summary['opening']['valid_rows']},
    )
    return job


def process_opening_commit(job_id):
    job = MigrationJob.objects.select_related('school', 'committed_by').filter(pk=job_id).first()
    if job is None or job.template != MigrationJob.Template.OPENING_BALANCES:
        return
    if job.status not in {MigrationJob.Status.COMMITTING, MigrationJob.Status.PARTIALLY_COMMITTED}:
        return
    _ensure_historical_years(job)
    while True:
        batch = list(
            MigrationRow.objects.filter(
                job=job,
                sheet__included=True,
                validation_status=MigrationRow.ValidationStatus.READY,
                commit_status=MigrationRow.CommitStatus.PENDING,
            )
            .select_related('sheet__migration_file', 'match_decision', 'match_decision__student')
            .order_by('source_row_number')[:BATCH_SIZE]
        )
        if not batch:
            break
        with transaction.atomic():
            for row in batch:
                try:
                    with transaction.atomic():
                        _commit_opening_row(job, row)
                except Exception as exc:
                    message = getattr(exc, 'detail', None) or str(exc)
                    if isinstance(message, dict):
                        message = next(iter(message.values()), message)
                    row.commit_status = MigrationRow.CommitStatus.FAILED
                    row.errors = [{'column': 'commit', 'message': str(message)[:500]}]
                    row.save(update_fields=['commit_status', 'errors', 'updated_at'])
            MigrationJob.objects.filter(pk=job.pk).update(heartbeat_at=timezone.now())
    open_rows = MigrationRow.objects.filter(job=job, sheet__included=True).exclude(
        commit_status__in=[
            MigrationRow.CommitStatus.COMMITTED,
            MigrationRow.CommitStatus.SKIPPED,
        ],
    ).exists()
    job.status = MigrationJob.Status.PARTIALLY_COMMITTED if open_rows else MigrationJob.Status.COMMITTED
    if job.status == MigrationJob.Status.COMMITTED:
        job.committed_at = timezone.now()
    job.heartbeat_at = timezone.now()
    job.save(update_fields=['status', 'committed_at', 'heartbeat_at', 'updated_at'])
    if job.status == MigrationJob.Status.COMMITTED:
        release_stored_file(job)
        record_migration_audit(
            school=job.school,
            job=job,
            actor=job.committed_by,
            action='commit',
            summary='Saved the opening balances.',
        )


def _commit_opening_row(job, row):
    proposal = row.proposal or {}
    if proposal.get('blocked') or proposal.get('action') not in {'balance', 'skip'}:
        raise ValidationError({'row': 'This row is not ready to save.'})
    if proposal.get('action') == 'skip':
        row.commit_status = MigrationRow.CommitStatus.SKIPPED
        row.committed_at = timezone.now()
        row.errors = proposal.get('warnings') or []
        row.save(update_fields=['commit_status', 'committed_at', 'errors', 'updated_at'])
        return

    migration_file = row.sheet.migration_file
    existing = MigrationCommitRecord.objects.filter(
        school=job.school,
        job_type=job.job_type,
        file_hash=migration_file.file_hash,
        sheet_name=row.sheet.sheet_name,
        source_row_number=row.source_row_number,
    ).first()
    if existing is not None:
        row.commit_status = MigrationRow.CommitStatus.COMMITTED
        row.committed_at = row.committed_at or timezone.now()
        row.save(update_fields=['commit_status', 'committed_at', 'updated_at'])
        return

    student = Student.objects.filter(pk=proposal.get('student_pk'), school=job.school).first()
    enrollment = proposal.get('enrollment') or {}
    term = resolved_term(job.school, enrollment.get('year'), enrollment.get('term'))
    if student is None or term is None:
        raise ValidationError({'row': 'The student or term could not be resolved.'})
    amount = Decimal(proposal.get('amount') or '0').quantize(Decimal('0.01'))
    if amount <= 0:
        raise ValidationError({'outstanding_balance': 'A negative balance cannot be imported.'})

    if MigrationOpeningBalance.objects.filter(school=job.school, student=student, term=term).exists():
        raise ValidationError({
            'outstanding_balance': 'This student already has an opening balance for this term. It was not changed.',
        })

    structure, item = _opening_fee_item(school=job.school, term=term, actor=job.committed_by)
    if StudentFee.objects.filter(student=student, fee_item=item).exists():
        raise ValidationError({
            'outstanding_balance': 'This student already has an opening balance for this term. It was not changed.',
        })
    fee = StudentFee(
        student=student,
        term=term,
        fee_structure=structure,
        fee_item=item,
        name=item.name,
        amount=amount,
    )
    fee.save()
    MigrationOpeningBalance.objects.create(
        school=job.school,
        job=job,
        student=student,
        term=term,
        student_fee=fee,
        file_hash=migration_file.file_hash,
        sheet_name=row.sheet.sheet_name,
        source_row_number=row.source_row_number,
        source_reference=proposal.get('source_reference') or '',
        notes=proposal.get('notes') or '',
        amount=amount,
        imported_by=job.committed_by,
    )
    if MigrationCommitRecord.objects.filter(
        school=job.school,
        source_transaction_id=f'opening:{student.pk}:{term.pk}',
    ).exists():
        raise ValidationError({
            'outstanding_balance': 'This student already has an opening balance for this term. It was not changed.',
        })
    MigrationCommitRecord.objects.create(
        school=job.school,
        job_type=job.job_type,
        file_hash=migration_file.file_hash,
        sheet_name=row.sheet.sheet_name,
        source_row_number=row.source_row_number,
        job=job,
        source_transaction_id=f'opening:{student.pk}:{term.pk}',
    )
    row.commit_status = MigrationRow.CommitStatus.COMMITTED
    row.committed_at = timezone.now()
    row.errors = []
    row.save(update_fields=['commit_status', 'committed_at', 'errors', 'updated_at'])


def _opening_fee_item(*, school, term, actor):
    structure = (
        FeeStructure.objects.select_for_update()
        .filter(school=school, term=term)
        .first()
    )
    if structure is None:
        structure = FeeStructure(
            school=school,
            term=term,
            created_by=actor,
            status=FeeStructure.Status.DRAFT,
            name='Opening balance',
        )
        structure.save()
    item = FeeItem.objects.filter(
        fee_structure=structure,
        is_migration_opening_balance=True,
    ).first()
    if item is None:
        item = FeeItem(
            fee_structure=structure,
            name='Opening balance',
            amount=Decimal('0.00'),
            description='Imported opening balance. Not part of the fee catalog.',
            applies_to_type=FeeItem.AppliesToType.SCHOOL,
            student_type=FeeItem.StudentType.ALL_STUDENTS,
            is_migration_opening_balance=True,
        )
        item.save()
    return structure, item
