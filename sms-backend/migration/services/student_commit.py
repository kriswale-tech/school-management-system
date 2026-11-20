"""Commit staged student and enrollment rows. Does not write fees or payments."""

from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from academics.models import ClassLevel, ClassStream, Level
from migration.models import (
    ExternalStudentReference,
    MigrationCommitRecord,
    MigrationJob,
    MigrationMatchDecision,
    MigrationRow,
)
from migration.services.audit import record_migration_audit
from migration.services.ingest import release_stored_file
from migration.services.student_plan import plan_for_job, plan_student_job
from schools.models import AcademicYear, Term
from students.models import ClassEnrollment, Parent, Student, StudentParent
from students.services import generate_student_id

BATCH_SIZE = 200
HEARTBEAT_SECONDS = 120
HISTORICAL_LEVEL_NAME = 'Historical classes'


def _year_bounds(label):
    parts = [part.strip() for part in (label or '').split('/')]
    if len(parts) != 2 or not all(part.isdigit() and len(part) == 4 for part in parts):
        return None
    start_year = int(parts[0])
    end_year = int(parts[1])
    if end_year < start_year:
        return None
    return start_year, end_year


def save_year_plan(*, job, label, start_date, end_date):
    bounds = _year_bounds(label)
    if bounds is None:
        raise ValidationError({'label': 'This year needs a name like 2020/2021.'})
    start_year, end_year = bounds
    if start_date.year != start_year:
        raise ValidationError({'start_date': f'The start date has to be in {start_year}.'})
    if end_date.year != end_year:
        raise ValidationError({'end_date': f'The end date has to be in {end_year}.'})
    if end_date <= start_date or (end_date - start_date).days < 3:
        raise ValidationError({'end_date': 'The year needs a real start and end at least three days apart.'})
    plans = [item for item in (job.summary or {}).get('year_plans', []) if item.get('label') != label]
    exists = AcademicYear.objects.filter(school=job.school, academic_year=label).exists()
    plans.append({
        'label': label,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'exists': exists,
    })
    summary = dict(job.summary or {})
    summary['year_plans'] = plans
    job.summary = summary
    job.save(update_fields=['summary', 'updated_at'])
    return plan_for_job(job)


def decide_match(*, row, actor, decision, student=None):
    match, _created = MigrationMatchDecision.objects.get_or_create(row=row)
    if row.job.template == MigrationJob.Template.OPENING_BALANCES and decision == MigrationMatchDecision.Decision.CREATE:
        raise ValidationError({'decision': 'Opening balances cannot add students. Link an existing student.'})
    if row.job.template == MigrationJob.Template.HISTORICAL_FINANCE and decision == MigrationMatchDecision.Decision.CREATE:
        raise ValidationError({'decision': 'Fee history cannot add students. Link an existing student.'})
    if decision == MigrationMatchDecision.Decision.LINK:
        if student is None or student.school_id != row.job.school_id:
            raise ValidationError({'student_id': 'Choose a student in this school.'})
        match.student = student
    elif decision == MigrationMatchDecision.Decision.CREATE:
        match.student = None
    else:
        raise ValidationError({'decision': 'Choose link or create.'})
    match.decision = decision
    match.decided_by = actor
    match.save(update_fields=['decision', 'student', 'decided_by', 'updated_at'])
    record_migration_audit(
        school=row.job.school,
        job=row.job,
        actor=actor,
        action='match',
        summary=f'{decision} for source row {row.source_row_number}.',
        payload={'row_id': str(row.id), 'student_id': str(student.id) if student else ''},
    )
    plan_for_job(row.job)
    row.refresh_from_db()
    return row


def decide_fields(*, row, actor, resolutions, guardian_decision):
    match, _created = MigrationMatchDecision.objects.get_or_create(row=row)
    cleaned = {}
    for field, choice in (resolutions or {}).items():
        if choice in {'keep', 'use_imported'}:
            cleaned[field] = choice
    match.field_resolution = {**(match.field_resolution or {}), **cleaned}
    if guardian_decision in {'keep', 'add_secondary'}:
        match.guardian_decision = guardian_decision
    match.decided_by = actor
    match.save(update_fields=['field_resolution', 'guardian_decision', 'decided_by', 'updated_at'])
    record_migration_audit(
        school=row.job.school,
        job=row.job,
        actor=actor,
        action='match',
        summary=f'Reviewed fields for source row {row.source_row_number}.',
        payload={'row_id': str(row.id)},
    )
    plan_for_job(row.job)
    row.refresh_from_db()
    return row


def _ready_new_students(job):
    count = 0
    rows = MigrationRow.objects.filter(
        job=job,
        sheet__included=True,
        validation_status=MigrationRow.ValidationStatus.READY,
        commit_status=MigrationRow.CommitStatus.PENDING,
    )
    for row in rows:
        proposal = row.proposal or {}
        if proposal.get('action') != 'create' or proposal.get('blocked'):
            continue
        lifecycle = proposal.get('lifecycle') or {}
        if lifecycle.get('is_active', True) and not lifecycle.get('is_graduated', False):
            count += 1
    return count


def begin_student_commit(*, job, actor):
    if job.job_type != MigrationJob.JobType.STUDENT_ENROLLMENT:
        raise ValidationError({'job': 'Only student and enrollment migration can be committed in this phase.'})
    if job.status in {MigrationJob.Status.COMMITTED, MigrationJob.Status.CANCELLED, MigrationJob.Status.ABANDONED}:
        raise ValidationError({'job': 'This migration is already finished.'})
    plan_student_job(job)
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
        from billing.services.capacity import ensure_can_add_students

        ensure_can_add_students(job.school, additional=_ready_new_students(job))
        job.status = MigrationJob.Status.COMMITTING
        job.committed_by = actor
        job.heartbeat_at = timezone.now()
        job.save(update_fields=['status', 'committed_by', 'heartbeat_at', 'updated_at'])
    record_migration_audit(
        school=job.school,
        job=job,
        actor=actor,
        action='commit',
        summary='Confirmed the student and enrollment migration.',
        payload={'ready_new_students': _ready_new_students(job)},
    )
    return job


def _match_decision(row):
    try:
        return row.match_decision
    except MigrationMatchDecision.DoesNotExist:
        return None


def row_can_be_saved(job, row):
    if row.validation_status != MigrationRow.ValidationStatus.READY:
        return False
    proposal = row.proposal or {}
    if proposal.get('blocked'):
        return False
    decision = _match_decision(row)
    if decision is not None and decision.decision == MigrationMatchDecision.Decision.CREATE:
        student_id = str((row.transformed_values or {}).get('student_id') or '').strip()
        if student_id and Student.objects.filter(school=job.school, student_id=student_id).exists():
            return False
    return True


def _unsaved_rows(job):
    return list(
        MigrationRow.objects.filter(job=job, sheet__included=True)
        .exclude(commit_status__in=[
            MigrationRow.CommitStatus.COMMITTED,
            MigrationRow.CommitStatus.SKIPPED,
        ])
        .select_related('match_decision')
    )


def resume_student_commit(*, job, actor):
    if job.status not in {MigrationJob.Status.COMMITTING, MigrationJob.Status.PARTIALLY_COMMITTED}:
        raise ValidationError({'job': 'This migration is not waiting to resume.'})
    if job.heartbeat_at and job.status == MigrationJob.Status.COMMITTING:
        age = timezone.now() - job.heartbeat_at
        if age.total_seconds() < HEARTBEAT_SECONDS:
            raise ValidationError({'job': 'This migration is already running.'})
    unsaved = _unsaved_rows(job)
    retryable = [row.id for row in unsaved if row_can_be_saved(job, row)]
    if not retryable:
        message = 'These students need a change before they can be saved. You can finish without them.'
        if job.template == MigrationJob.Template.OPENING_BALANCES:
            message = 'These balances need a change before they can be saved. You can finish without them.'
        elif job.template == MigrationJob.Template.HISTORICAL_FINANCE:
            message = 'These rows need a change before they can be saved. You can finish without them.'
        raise ValidationError({'job': message})
    MigrationRow.objects.filter(
        pk__in=retryable,
        commit_status=MigrationRow.CommitStatus.FAILED,
    ).update(commit_status=MigrationRow.CommitStatus.PENDING)
    job.status = MigrationJob.Status.COMMITTING
    job.heartbeat_at = timezone.now()
    job.save(update_fields=['status', 'heartbeat_at', 'updated_at'])
    record_migration_audit(
        school=job.school,
        job=job,
        actor=actor,
        action='commit',
        summary='Resumed the student and enrollment migration.',
    )
    return job


def finish_without_unsaved(*, job, actor):
    if job.status == MigrationJob.Status.COMMITTING and job.heartbeat_at:
        age = timezone.now() - job.heartbeat_at
        if age.total_seconds() < HEARTBEAT_SECONDS:
            raise ValidationError({'job': 'This import is still saving.'})
    if job.status not in {MigrationJob.Status.COMMITTING, MigrationJob.Status.PARTIALLY_COMMITTED}:
        raise ValidationError({'job': 'This import is not waiting to finish.'})
    unsaved = MigrationRow.objects.filter(job=job, sheet__included=True).exclude(
        commit_status__in=[
            MigrationRow.CommitStatus.COMMITTED,
            MigrationRow.CommitStatus.SKIPPED,
        ],
    )
    if not unsaved.exists():
        raise ValidationError({'job': 'Every student in this import is already saved.'})
    unsaved.update(commit_status=MigrationRow.CommitStatus.SKIPPED)
    job.status = MigrationJob.Status.COMMITTED
    job.committed_at = job.committed_at or timezone.now()
    job.heartbeat_at = timezone.now()
    job.save(update_fields=['status', 'committed_at', 'heartbeat_at', 'updated_at'])
    release_stored_file(job)
    record_migration_audit(
        school=job.school,
        job=job,
        actor=actor,
        action='commit',
        summary='Finished the import and left the unsaved students out.',
    )
    return job


def process_student_commit(job_id):
    job = MigrationJob.objects.select_related('school', 'committed_by').filter(pk=job_id).first()
    if job is None or job.template in {
        MigrationJob.Template.OPENING_BALANCES,
        MigrationJob.Template.HISTORICAL_FINANCE,
    }:
        return
    if job.status not in {MigrationJob.Status.COMMITTING, MigrationJob.Status.PARTIALLY_COMMITTED}:
        return
    from billing.services.capacity import ensure_can_add_students

    ensure_can_add_students(job.school, additional=_ready_new_students(job))
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
                        _commit_one(job, row)
                except Exception as exc:
                    message = getattr(exc, 'detail', None) or str(exc)
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


def _ensure_historical_years(job):
    active = AcademicYear.objects.filter(school=job.school, is_active=True).first()
    for plan in (job.summary or {}).get('year_plans', []):
        label = plan.get('label')
        if not label or AcademicYear.objects.filter(school=job.school, academic_year=label).exists():
            continue
        start = date.fromisoformat(plan['start_date'])
        end = date.fromisoformat(plan['end_date'])
        year = AcademicYear.objects.create(
            school=job.school,
            academic_year=label,
            start_date=start,
            end_date=end,
            is_active=False,
        )
        _create_three_terms(job.school, year, start, end)
    if active is not None:
        active.refresh_from_db()
        if not active.is_active:
            raise ValidationError({'academic_year': 'The active academic year was changed during migration.'})


def _create_three_terms(school, year, start, end):
    span = (end - start).days
    first_end = start + timedelta(days=span // 3)
    second_end = start + timedelta(days=(span // 3) * 2)
    ranges = (
        (Term.TermChoices.FIRST_TERM, start, first_end),
        (Term.TermChoices.SECOND_TERM, first_end + timedelta(days=1), second_end),
        (Term.TermChoices.THIRD_TERM, second_end + timedelta(days=1), end),
    )
    for key, term_start, term_end in ranges:
        Term.objects.create(
            school=school,
            academic_year=year,
            term=key,
            start_date=term_start,
            end_date=term_end,
            is_active=False,
        )


def _commit_one(job, row):
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

    proposal = row.proposal or {}
    if proposal.get('blocked'):
        raise ValidationError('This row still needs review.')
    match = row.match_decision
    values = row.transformed_values or {}
    created = False
    if match.decision == MigrationMatchDecision.Decision.LINK and match.student_id:
        student = match.student
        _apply_student_updates(student, values, match.field_resolution or {}, proposal.get('fills') or [])
    elif match.decision == MigrationMatchDecision.Decision.CREATE:
        student = _create_student(job, values)
        created = True
    else:
        raise ValidationError('Choose whether to link or create this student.')

    if values.get('external_id'):
        reference, _created = ExternalStudentReference.objects.get_or_create(
            school=job.school,
            source_system=job.source_system or '',
            external_id=str(values['external_id']).strip(),
            defaults={'student': student},
        )
        if reference.student_id != student.id:
            raise ValidationError('That external ID is already linked to a different student.')
    _apply_guardian(job, student, values, match)
    _apply_enrollment(job, student, proposal.get('enrollment') or {}, values)
    if created:
        _apply_lifecycle(student, proposal.get('lifecycle') or {})
    MigrationCommitRecord.objects.create(
        school=job.school,
        job_type=job.job_type,
        file_hash=migration_file.file_hash,
        sheet_name=row.sheet.sheet_name,
        source_row_number=row.source_row_number,
        job=job,
    )
    proposal = dict(proposal)
    proposal['result'] = {
        'student_id': str(student.id),
        'created': created,
    }
    row.proposal = proposal
    row.commit_status = MigrationRow.CommitStatus.COMMITTED
    row.committed_at = timezone.now()
    row.save(update_fields=['proposal', 'commit_status', 'committed_at', 'updated_at'])


def _create_student(job, values):
    from migration.services.student_plan import _iso_date, _student_name, _text

    provided = _text(values.get('student_id'))
    if provided and Student.objects.filter(school=job.school, student_id=provided).exists():
        raise ValidationError(f'Student ID {provided} already exists. Link that student instead of creating another.')
    student_id = provided or generate_student_id(school=job.school)
    first, last = _student_name(values)
    return Student.objects.create(
        school=job.school,
        student_id=student_id,
        first_name=first,
        last_name=last,
        other_names=_text(values.get('other_names')),
        gender=_text(values.get('gender')),
        date_of_birth=date.fromisoformat(_iso_date(values.get('date_of_birth'))),
        admission_date=date.fromisoformat(_iso_date(values.get('admission_date'))),
        address=_text(values.get('address')),
    )


def _apply_student_updates(student, values, resolutions, fills):
    from migration.services.student_plan import _iso_date, _text

    updates = []
    allowed = {item['field'] for item in fills}
    allowed.update(field for field, choice in resolutions.items() if choice == 'use_imported')
    for field in allowed:
        raw = values.get(field)
        if field in {'date_of_birth', 'admission_date'}:
            parsed = _iso_date(raw)
            if not parsed:
                continue
            setattr(student, field, date.fromisoformat(parsed))
        else:
            setattr(student, field, _text(raw))
        updates.append(field)
    if updates:
        student.save(update_fields=[*updates, 'updated_at'])


def _apply_guardian(job, student, values, match):
    from migration.services.student_plan import _phone, _text

    proposal_phone = _phone(values.get('guardian_phone'))
    name = _text(values.get('guardian_name')) or 'Guardian'
    if not proposal_phone:
        return
    parent = Parent.objects.filter(school=job.school, phone_number=proposal_phone).first()
    email = _text(values.get('guardian_email'))
    if parent is None:
        parent = Parent.objects.create(
            school=job.school,
            name=name,
            phone_number=proposal_phone,
            email=email,
        )
    else:
        updates = []
        if not parent.name and name:
            parent.name = name
            updates.append('name')
        if email and not parent.email:
            parent.email = email
            updates.append('email')
        if updates:
            parent.save(update_fields=[*updates, 'updated_at'])
    relationship = _text(values.get('guardian_relationship')) or StudentParent.RelationshipChoices.GUARDIAN
    if relationship not in StudentParent.RelationshipChoices.values:
        relationship = StudentParent.RelationshipChoices.GUARDIAN
    if StudentParent.objects.filter(student=student, parent=parent).exists():
        return
    primary = StudentParent.objects.filter(student=student, is_primary=True).first()
    if primary and primary.parent_id != parent.id:
        if match.guardian_decision == 'keep':
            return
        if match.guardian_decision != 'add_secondary':
            raise ValidationError('The primary guardian still needs a decision.')
        StudentParent.objects.create(
            student=student,
            parent=parent,
            relationship=relationship,
            is_primary=False,
        )
        return
    StudentParent.objects.create(
        student=student,
        parent=parent,
        relationship=relationship,
        is_primary=primary is None,
    )


def _apply_enrollment(job, student, enrollment, values):
    action = enrollment.get('action')
    if action in {None, '', 'none', 'missing'}:
        return
    year = AcademicYear.objects.filter(school=job.school, academic_year=enrollment.get('year')).first()
    term = Term.objects.filter(academic_year=year, term=enrollment.get('term')).first() if year else None
    if term is None:
        raise ValidationError('The academic year or term for this enrollment is not available.')
    if ClassEnrollment.objects.filter(student=student, term=term).exists():
        return
    if action == 'snapshot':
        stream = _snapshot_stream(job.school, enrollment.get('class_name') or '')
        resolution = 'snapshot'
    else:
        stream = ClassStream.objects.select_related('class_level').filter(
            id=enrollment.get('stream_id'),
            class_level__school=job.school,
        ).first()
        if stream is None:
            raise ValidationError('The class for this enrollment could not be found.')
        if action == 'current' and stream.is_migration_snapshot:
            raise ValidationError('A current-term enrollment cannot use a historical snapshot.')
        resolution = 'operational' if action == 'current' else 'historical_existing'
    created = ClassEnrollment.objects.create(
        student=student,
        term=term,
        stream=stream,
        is_new_student=False,
        source_class_name=enrollment.get('class_name') or '',
        class_resolution=resolution,
    )
    if enrollment.get('is_new_student_explicit'):
        created.is_new_student = bool(enrollment.get('is_new_student'))
        created.save(update_fields=['is_new_student', 'updated_at'])
    else:
        _mark_earliest_enrollment(student, created)


def _snapshot_stream(school, class_name):
    level = Level.objects.filter(
        school=school,
        name=HISTORICAL_LEVEL_NAME,
        is_migration_snapshot=True,
    ).first()
    if level is None:
        level = Level(
            school=school,
            name=HISTORICAL_LEVEL_NAME,
            is_active=False,
            is_system_generated=False,
            is_migration_snapshot=True,
            order=99,
        )
        level.full_clean()
        level.save()
    class_level = ClassLevel.objects.filter(level=level, name=class_name[:255]).first()
    if class_level is None:
        class_level = ClassLevel(
            level=level,
            school=school,
            name=class_name[:255],
            is_active=False,
            is_system_generated=False,
            is_migration_snapshot=True,
        )
        class_level.save()
    stream = class_level.streams.filter(is_default=True).first()
    if stream is None:
        stream = ClassStream(
            class_level=class_level,
            name='',
            is_default=True,
            is_active=False,
            is_migration_snapshot=True,
        )
        stream.save()
    return stream


def _mark_earliest_enrollment(student, created):
    enrollments = list(student.enrollments.select_related('term'))
    earliest = min(enrollments, key=lambda item: (item.term.start_date, item.created_at))
    if created.id == earliest.id and not created.is_new_student:
        created.is_new_student = True
        created.save(update_fields=['is_new_student', 'updated_at'])
    elif created.id != earliest.id and created.is_new_student:
        created.is_new_student = False
        created.save(update_fields=['is_new_student', 'updated_at'])


def _apply_lifecycle(student, lifecycle):
    if not lifecycle.get('apply', True):
        return
    active = bool(lifecycle.get('is_active', True))
    graduated = bool(lifecycle.get('is_graduated', False))
    reason = lifecycle.get('leave_reason') or ''
    if reason not in Student.LeaveReason.values:
        reason = ''
    student.is_active = active
    student.is_graduated = graduated
    if not active:
        student.leave_reason = reason
        student.left_at = timezone.now()
    student.save(update_fields=['is_active', 'is_graduated', 'leave_reason', 'left_at', 'updated_at'])
