"""Write historical charges and payments. No receipts, notices, or automatic credits."""

from collections import defaultdict
from datetime import datetime, time
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from fees.models import FeeItem, FeeStructure, Payment, PaymentAllocation, StudentFee, StudentFeeCredit
from migration.models import (
    MigrationCommitRecord,
    MigrationHistoricalCharge,
    MigrationHistoricalPayment,
    MigrationJob,
    MigrationOpeningBalance,
    MigrationRow,
)
from migration.services.audit import record_migration_audit
from migration.services.historical_plan import plan_historical_job
from migration.services.ingest import release_stored_file
from migration.services.opening_plan import resolved_term
from migration.services.student_commit import _ensure_historical_years
from students.models import Student

BATCH_SIZE = 200


def begin_historical_commit(*, job, actor):
    if job.template != MigrationJob.Template.HISTORICAL_FINANCE:
        raise ValidationError({'job': 'This commit is only for fee history.'})
    if job.job_type != MigrationJob.JobType.FEE_FINANCIAL_HISTORY:
        raise ValidationError({'job': 'Fee history uses the fee import.'})
    if job.status in {MigrationJob.Status.COMMITTED, MigrationJob.Status.CANCELLED, MigrationJob.Status.ABANDONED}:
        raise ValidationError({'job': 'This migration is already finished.'})
    summary = plan_historical_job(job)
    history = summary['history']
    if history['valid_rows'] < 1:
        raise ValidationError({'job': 'Nothing in this file is ready to save.'})
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
        summary=(
            f'Confirmed fee history of GHS {history["charge_total"]} in charges '
            f'and GHS {history["payment_total"]} in payments.'
        ),
        payload=history,
    )
    return job


def process_historical_commit(job_id):
    job = MigrationJob.objects.select_related('school', 'committed_by').filter(pk=job_id).first()
    if job is None or job.template != MigrationJob.Template.HISTORICAL_FINANCE:
        return
    if job.status not in {MigrationJob.Status.COMMITTING, MigrationJob.Status.PARTIALLY_COMMITTED}:
        return
    _ensure_historical_years(job)
    while True:
        batch = list(
            MigrationRow.objects.filter(
                job=job,
                sheet__included=True,
                sheet__migration_file__role='charges',
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
                        _commit_charge_row(job, row)
                except Exception as exc:
                    _fail_row(row, exc)
            MigrationJob.objects.filter(pk=job.pk).update(heartbeat_at=timezone.now())
    pending_payments = list(
        MigrationRow.objects.filter(
            job=job,
            sheet__included=True,
            sheet__migration_file__role='payments',
            validation_status=MigrationRow.ValidationStatus.READY,
            commit_status=MigrationRow.CommitStatus.PENDING,
        ).select_related('sheet__migration_file', 'match_decision', 'match_decision__student')
    )
    groups = defaultdict(list)
    for row in pending_payments:
        groups[(row.proposal or {}).get('reference_key') or str(row.id)].append(row)
    processed = 0
    for rows in groups.values():
        try:
            with transaction.atomic():
                _commit_payment_group(job, rows)
        except Exception as exc:
            for row in rows:
                _fail_row(row, exc)
        processed += 1
        if processed % BATCH_SIZE == 0:
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
            summary='Saved the fee history.',
        )


def _fail_row(row, exc):
    message = getattr(exc, 'detail', None) or str(exc)
    if isinstance(message, dict):
        message = next(iter(message.values()), message)
    if isinstance(message, list):
        message = message[0] if message else 'This row was not saved.'
    row.commit_status = MigrationRow.CommitStatus.FAILED
    row.errors = [{'column': 'commit', 'message': str(message)[:500]}]
    row.save(update_fields=['commit_status', 'errors', 'updated_at'])


def _commit_charge_row(job, row):
    proposal = row.proposal or {}
    if proposal.get('blocked') or proposal.get('action') not in {'charge', 'skip'}:
        raise ValidationError({'row': 'This row is not ready to save.'})
    if proposal.get('action') == 'skip':
        _skip_row(row)
        return
    migration_file = row.sheet.migration_file
    if _commit_record_exists(job, migration_file, row):
        _mark_committed(row)
        return
    student, term = _student_and_term(job, proposal)
    amount = Decimal(proposal.get('amount') or '0').quantize(Decimal('0.01'))
    if amount <= 0:
        raise ValidationError({'amount': 'A negative amount cannot be imported.'})
    if MigrationOpeningBalance.objects.filter(school=job.school, student=student, term=term).exists():
        raise ValidationError({'amount': 'This term already has an opening balance. These charges were left out.'})
    fee_name = proposal.get('fee_name') or ''
    if MigrationHistoricalCharge.objects.filter(
        school=job.school,
        student=student,
        term=term,
        fee_name=fee_name,
    ).exists():
        raise ValidationError({'fee_item': 'This fee line was already imported. It was not changed.'})
    structure, item = _historical_fee_item(
        school=job.school,
        term=term,
        fee_name=fee_name,
        fee_label=proposal.get('fee_label') or fee_name,
        actor=job.committed_by,
    )
    if StudentFee.objects.filter(student=student, fee_item=item).exists():
        raise ValidationError({'fee_item': 'This fee line was already imported. It was not changed.'})
    fee = StudentFee(
        student=student,
        term=term,
        fee_structure=structure,
        fee_item=item,
        name=item.name,
        amount=amount,
    )
    fee.save()
    MigrationHistoricalCharge.objects.create(
        school=job.school,
        job=job,
        student=student,
        term=term,
        student_fee=fee,
        fee_name=fee_name,
        file_hash=migration_file.file_hash,
        sheet_name=row.sheet.sheet_name,
        source_row_number=row.source_row_number,
        source_reference=proposal.get('source_reference') or '',
        notes=proposal.get('notes') or '',
        amount=amount,
        imported_by=job.committed_by,
    )
    _write_commit_record(
        job,
        migration_file,
        row,
        f'charge:{student.pk}:{term.pk}:{fee_name}',
    )
    _mark_committed(row)


def _commit_payment_group(job, rows):
    proposals = [row.proposal or {} for row in rows]
    if any(item.get('blocked') or item.get('action') not in {'payment', 'advance'} for item in proposals):
        raise ValidationError({'row': 'This payment is not ready to save.'})
    reference_key = proposals[0].get('reference_key') or ''
    if not reference_key:
        raise ValidationError({'payment_reference': 'Enter the payment reference.'})
    existing = MigrationHistoricalPayment.objects.filter(school=job.school, reference_key=reference_key).first()
    if existing is not None:
        if existing.job_id != job.id:
            raise ValidationError({'payment_reference': 'This payment reference was already imported. It was not changed.'})
        for row in rows:
            _mark_committed(row)
        return
    student_ids = {item.get('student_pk') for item in proposals}
    if len(student_ids) != 1:
        raise ValidationError({'payment_reference': 'These rows use one payment reference but the student does not match.'})
    student = Student.objects.filter(pk=next(iter(student_ids)), school=job.school).first()
    if student is None or job.committed_by_id is None:
        raise ValidationError({'row': 'The student or term could not be resolved.'})
    resolved = []
    for row, proposal in zip(rows, proposals):
        term = resolved_term(job.school, (proposal.get('enrollment') or {}).get('year'), (proposal.get('enrollment') or {}).get('term'))
        if term is None:
            raise ValidationError({'row': 'The student or term could not be resolved.'})
        if MigrationOpeningBalance.objects.filter(school=job.school, student=student, term=term).exists():
            raise ValidationError({'amount': 'This term already has an opening balance. These payments were left out.'})
        resolved.append((row, proposal, term, Decimal(proposal.get('amount') or '0').quantize(Decimal('0.01'))))
    payment_type = proposals[0].get('payment_type') or 'ordinary'
    total = sum((item[3] for item in resolved), Decimal('0.00'))
    if total <= 0:
        raise ValidationError({'amount': 'A payment amount must be greater than zero.'})
    primary = min(resolved, key=lambda item: (item[2].start_date, item[2].created_at))
    paid_on = datetime.strptime(proposals[0]['paid_on'], '%Y-%m-%d').date()
    paid_at = timezone.make_aware(datetime.combine(paid_on, time(12, 0)))
    payment = Payment(
        student=student,
        term=primary[2],
        amount=total,
        payment_method=proposals[0]['payment_method'],
        paid_at=paid_at,
        payment_reference=proposals[0].get('payment_reference') or '',
        legacy_receipt_number=proposals[0].get('legacy_receipt_number') or '',
        payment_notes=proposals[0].get('notes') or '',
        recorded_by=job.committed_by,
    )
    payment.save(skip_default_allocation=True)
    if payment_type == 'ordinary':
        for _row, _proposal, term, amount in resolved:
            PaymentAllocation.objects.create(payment=payment, term=term, amount=amount)
    else:
        StudentFeeCredit.objects.create(
            student=student,
            school=job.school,
            amount=total,
            remaining_amount=total,
            status=StudentFeeCredit.Status.AVAILABLE,
            source_payment=payment,
            is_migration_hold=True,
            notes='Imported historical advance.',
        )
    MigrationHistoricalPayment.objects.create(
        school=job.school,
        job=job,
        student=student,
        payment=payment,
        reference_key=reference_key,
        legacy_receipt_number=proposals[0].get('legacy_receipt_number') or '',
        payment_type=payment_type,
        imported_by=job.committed_by,
    )
    for index, (row, _proposal, term, _amount) in enumerate(resolved):
        source_id = f'payment:{reference_key}' if index == 0 else f'payment:{reference_key}:{term.pk}'
        _write_commit_record(job, row.sheet.migration_file, row, source_id)
        _mark_committed(row)


def _historical_fee_item(*, school, term, fee_name, fee_label, actor):
    structure = FeeStructure.objects.select_for_update().filter(school=school, term=term).first()
    if structure is None:
        structure = FeeStructure(
            school=school,
            term=term,
            created_by=actor,
            status=FeeStructure.Status.DRAFT,
            name='Fee history',
        )
        structure.save()
    item = FeeItem.objects.filter(
        fee_structure=structure,
        is_migration_historical=True,
        name__iexact=fee_label,
    ).first()
    if item is None:
        item = FeeItem(
            fee_structure=structure,
            name=fee_label[:255],
            amount=Decimal('0.00'),
            description='Imported historical charge. Not part of the fee catalog.',
            applies_to_type=FeeItem.AppliesToType.SCHOOL,
            student_type=FeeItem.StudentType.ALL_STUDENTS,
            is_migration_historical=True,
        )
        item.save()
    return structure, item


def _student_and_term(job, proposal):
    student = Student.objects.filter(pk=proposal.get('student_pk'), school=job.school).first()
    enrollment = proposal.get('enrollment') or {}
    term = resolved_term(job.school, enrollment.get('year'), enrollment.get('term'))
    if student is None or term is None:
        raise ValidationError({'row': 'The student or term could not be resolved.'})
    return student, term


def _commit_record_exists(job, migration_file, row):
    return MigrationCommitRecord.objects.filter(
        school=job.school,
        job_type=job.job_type,
        file_hash=migration_file.file_hash,
        sheet_name=row.sheet.sheet_name,
        source_row_number=row.source_row_number,
    ).exists()


def _write_commit_record(job, migration_file, row, source_transaction_id):
    if MigrationCommitRecord.objects.filter(
        school=job.school,
        source_transaction_id=source_transaction_id,
    ).exists():
        raise ValidationError({'row': 'This row was already imported. It was not changed.'})
    MigrationCommitRecord.objects.create(
        school=job.school,
        job_type=job.job_type,
        file_hash=migration_file.file_hash,
        sheet_name=row.sheet.sheet_name,
        source_row_number=row.source_row_number,
        job=job,
        source_transaction_id=source_transaction_id,
    )


def _mark_committed(row):
    row.commit_status = MigrationRow.CommitStatus.COMMITTED
    row.committed_at = timezone.now()
    row.errors = []
    row.save(update_fields=['commit_status', 'committed_at', 'errors', 'updated_at'])


def _skip_row(row):
    row.commit_status = MigrationRow.CommitStatus.SKIPPED
    row.committed_at = timezone.now()
    row.errors = (row.proposal or {}).get('warnings') or []
    row.save(update_fields=['commit_status', 'committed_at', 'errors', 'updated_at'])
