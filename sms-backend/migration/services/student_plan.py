"""Preview what a student migration would create. This does not write students."""

from datetime import date, datetime

from django.db.models import Prefetch

from migration.models import ExternalStudentReference, MigrationJob, MigrationMatchDecision, MigrationRow
from migration.services.class_resolution import (
    apply_saved,
    is_operational,
    load_class_memory,
    load_streams,
    resolve_placement,
    saved_map,
)
from migration.services.reconciliation import apply_row_enums, enum_memory
from migration.services.staging import preview_summary
from shared.helpers import format_phone_number
from students.models import Parent, Student, StudentParent

COMPARE_FIELDS = (
    'first_name',
    'last_name',
    'other_names',
    'gender',
    'date_of_birth',
    'admission_date',
    'address',
)
TERM_ALIASES = {
    '1': 'first_term',
    'first': 'first_term',
    'first term': 'first_term',
    'first_term': 'first_term',
    '2': 'second_term',
    'second': 'second_term',
    'second term': 'second_term',
    'second_term': 'second_term',
    '3': 'third_term',
    'third': 'third_term',
    'third term': 'third_term',
    'third_term': 'third_term',
}


def _text(value):
    return str(value or '').strip()


def _key(value):
    return ' '.join(_text(value).casefold().split())


def _parse_bool(value, default):
    text = _key(value)
    if not text:
        return default
    if text in {'1', 'true', 'yes', 'y', 'active'}:
        return True
    if text in {'0', 'false', 'no', 'n', 'inactive', 'left'}:
        return False
    return default


def _student_name(values):
    first = _text(values.get('first_name'))
    last = _text(values.get('last_name'))
    if first or last:
        return first, last
    parts = _text(values.get('full_name')).split()
    if not parts:
        return '', ''
    if len(parts) == 1:
        return parts[0], ''
    return parts[0], parts[-1]


def _iso_date(value):
    text = _text(value)
    if not text:
        return ''
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        return ''


def _phone(value):
    text = _text(value)
    if not text:
        return ''
    try:
        return format_phone_number(text)
    except ValueError:
        return ''


def _candidate(student, reason):
    return {
        'id': str(student.id),
        'student_id': student.student_id,
        'name': f'{student.first_name} {student.last_name}'.strip(),
        'date_of_birth': student.date_of_birth.isoformat(),
        'reason': reason,
    }


def _index_students(school):
    students = list(
        Student.objects.filter(school=school).prefetch_related(
            Prefetch(
                'parent_links',
                queryset=StudentParent.objects.select_related('parent'),
            ),
        )
    )
    by_id = {}
    by_name_dob = {}
    by_name_phone = {}
    for student in students:
        by_id.setdefault(student.student_id.casefold(), []).append(student)
        dob = student.date_of_birth.isoformat()
        name = (_key(student.first_name), _key(student.last_name))
        by_name_dob.setdefault((*name, dob), []).append(student)
        for link in student.parent_links.all():
            phone = link.parent.phone_number
            if phone:
                by_name_phone.setdefault((*name, phone), []).append(student)
    return students, by_id, by_name_dob, by_name_phone


def _stored(student, field):
    value = getattr(student, field)
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return _text(value)


def _field_diff(student, values):
    fills = []
    conflicts = []
    for field in COMPARE_FIELDS:
        imported = _iso_date(values.get(field)) if field in {'date_of_birth', 'admission_date'} else _text(values.get(field))
        if field in {'first_name', 'last_name'} and not imported:
            first, last = _student_name(values)
            imported = first if field == 'first_name' else last
        current = _stored(student, field)
        if not imported or _key(imported) == _key(current):
            continue
        if not current:
            fills.append({'field': field, 'imported': imported})
        else:
            conflicts.append({'field': field, 'current': current, 'imported': imported})
    return fills, conflicts


def _corrections(row):
    return dict((row.proposal or {}).get('corrections') or {})


def _overlay_values(values, corrections):
    updated = dict(values)
    for key, value in corrections.items():
        if key == 'stream_id' or value in (None, ''):
            continue
        updated[key] = value
    return updated


def _normalize_term(value):
    return TERM_ALIASES.get(_key(value), '')


def plan_student_job(job):
    if job.job_type != MigrationJob.JobType.STUDENT_ENROLLMENT:
        summary = preview_summary(job)
        job.summary = summary
        job.save(update_fields=['summary', 'updated_at'])
        return summary

    school = job.school
    rows = list(
        MigrationRow.objects.filter(job=job, sheet__included=True)
        .select_related('sheet__migration_file', 'match_decision')
        .prefetch_related('sheet__field_mappings')
        .order_by('source_row_number')
    )
    _students, by_id, by_name_dob, by_name_phone = _index_students(school)
    references = {
        (ref.source_system, ref.external_id.casefold()): ref.student
        for ref in ExternalStudentReference.objects.filter(school=school).select_related('student')
    }
    parents = {
        parent.phone_number: parent
        for parent in Parent.objects.filter(school=school)
    }
    from schools.models import AcademicYear, Term

    active_term = (
        Term.objects.filter(school=school, is_active=True)
        .select_related('academic_year')
        .first()
    )
    years = {
        year.academic_year: year
        for year in AcademicYear.objects.filter(school=school).prefetch_related('terms')
    }
    year_plans = {
        item['label']: item
        for item in (job.summary or {}).get('year_plans', [])
        if item.get('label')
    }
    streams = load_streams(school.id) if job.template else []
    saved = saved_map(job) if job.template else {}
    class_memory = load_class_memory(school) if job.template else {}
    enums = enum_memory(school) if job.template else {}
    id_counts = {}
    for row in rows:
        student_id = _text(row.transformed_values.get('student_id'))
        if student_id:
            id_counts[student_id.casefold()] = id_counts.get(student_id.casefold(), 0) + 1

    for row in rows:
        if row.validation_status == MigrationRow.ValidationStatus.BLOCKED and not _match_only_block(row):
            row.proposal = {
                'action': 'blocked',
                'reasons': row.errors,
                'block_reasons': row.errors,
                'corrections': _corrections(row),
                'student_label': (row.proposal or {}).get('student_label') or '',
            }
            continue
        planner = _plan_history_row if job.template == MigrationJob.Template.ENROLLMENT_HISTORY else _plan_row
        proposal, decision_state = planner(
            job=job,
            row=row,
            by_id=by_id,
            by_name_dob=by_name_dob,
            by_name_phone=by_name_phone,
            references=references,
            parents=parents,
            years=years,
            year_plans=year_plans,
            active_term=active_term,
            duplicate_ids=id_counts,
            streams=streams,
            saved=saved,
            class_memory=class_memory,
            enums=enums,
        )
        _save_decision(row, decision_state)
        row.proposal = proposal
        row.validation_status = (
            MigrationRow.ValidationStatus.BLOCKED
            if proposal.get('blocked')
            else MigrationRow.ValidationStatus.READY
        )
        if proposal.get('blocked'):
            row.errors = proposal.get('block_reasons', [])

    MigrationRow.objects.bulk_update(rows, ['proposal', 'validation_status', 'errors', 'transformed_values', 'updated_at'])
    summary = preview_summary(job)
    summary['plan'] = _summarize(rows, year_plans)
    summary['year_plans'] = list(year_plans.values())
    job.summary = summary
    job.save(update_fields=['summary', 'updated_at'])
    return summary


def plan_for_job(job):
    if job.template == MigrationJob.Template.OPENING_BALANCES:
        from migration.services.opening_plan import plan_opening_job
        return plan_opening_job(job)
    if job.template == MigrationJob.Template.HISTORICAL_FINANCE:
        from migration.services.historical_plan import plan_historical_job
        return plan_historical_job(job)
    return plan_student_job(job)


def _match_only_block(row):
    return any(
        item.get('column') in {
            'match',
            'guardian',
            'enrollment',
            'conflict',
            'gender',
            'student_status',
            'guardian_relationship',
            'is_new_student',
            'student_id',
        }
        for item in (row.errors or [])
    )


def _plan_row(*, job, row, by_id, by_name_dob, by_name_phone, references, parents, years, year_plans, active_term, duplicate_ids, streams=None, saved=None, class_memory=None, enums=None):
    values, enum_blocks = apply_row_enums(job, row, enums or {})
    corrections = _corrections(row)
    values = _overlay_values(values, corrections)
    enum_blocks = [item for item in enum_blocks if item.get('column') not in corrections]
    row.transformed_values = values
    try:
        existing_decision = row.match_decision
    except MigrationMatchDecision.DoesNotExist:
        existing_decision = None
    first, last = _student_name(values)
    student_id = _text(values.get('student_id'))
    external_id = _text(values.get('external_id'))
    source = job.source_system or ''
    block_reasons = []
    kind = MigrationMatchDecision.Kind.NONE
    reason = 'No existing student matched an exact identifier.'
    candidates = []
    student = None

    duplicate_warning = ''
    if student_id and duplicate_ids.get(student_id.casefold(), 0) > 1:
        duplicate_warning = f'Student ID {student_id} is used more than once in this file.'
        block_reasons.append({
            'column': 'student_id',
            'message': f'Student ID {student_id} is used more than once in this file. Change it on one of these rows before saving.',
        })

    ref_student = references.get((source, external_id.casefold())) if external_id else None
    id_students = by_id.get(student_id.casefold(), []) if student_id else []
    if ref_student and id_students and ref_student.id not in {item.id for item in id_students}:
        kind = MigrationMatchDecision.Kind.AMBIGUOUS
        reason = 'The external ID and student ID point at different students.'
        candidates = [_candidate(ref_student, 'External reference'), *[_candidate(item, 'Student ID') for item in id_students]]
        block_reasons.append({'column': 'match', 'message': reason})
    elif ref_student is not None:
        kind = MigrationMatchDecision.Kind.EXACT
        reason = 'External student reference.'
        student = ref_student
        candidates = [_candidate(student, reason)]
    elif len(id_students) == 1:
        kind = MigrationMatchDecision.Kind.EXACT
        reason = 'Exact student ID.'
        student = id_students[0]
        candidates = [_candidate(student, reason)]
    elif len(id_students) > 1:
        kind = MigrationMatchDecision.Kind.AMBIGUOUS
        reason = 'More than one student has this student ID.'
        candidates = [_candidate(item, reason) for item in id_students]
        block_reasons.append({'column': 'match', 'message': reason})
    elif kind != MigrationMatchDecision.Kind.AMBIGUOUS:
        dob = _iso_date(values.get('date_of_birth'))
        phone = _phone(values.get('guardian_phone'))
        probable = []
        if first and last and dob:
            probable = by_name_dob.get((_key(first), _key(last), dob), [])
            probable_reason = 'Same name and date of birth.'
        else:
            probable_reason = ''
        if not probable and first and last and phone:
            probable = by_name_phone.get((_key(first), _key(last), phone), [])
            probable_reason = 'Same name and guardian phone.'
        if len(probable) == 1:
            kind = MigrationMatchDecision.Kind.PROBABLE
            reason = probable_reason
            candidates = [_candidate(probable[0], reason)]
            block_reasons.append({
                'column': 'match',
                'message': f'{reason} Confirm this student or create a new record.',
            })
        elif len(probable) > 1:
            kind = MigrationMatchDecision.Kind.AMBIGUOUS
            reason = f'{probable_reason} Several students fit.'
            candidates = [_candidate(item, probable_reason) for item in probable]
            block_reasons.append({'column': 'match', 'message': reason})

    decision = existing_decision.decision if existing_decision else MigrationMatchDecision.Decision.PENDING
    chosen = existing_decision.student if existing_decision and existing_decision.student_id else None
    if kind == MigrationMatchDecision.Kind.EXACT and student is not None and not block_reasons:
        decision = MigrationMatchDecision.Decision.LINK
        chosen = student
    elif decision == MigrationMatchDecision.Decision.LINK and chosen is not None:
        pass
    elif decision == MigrationMatchDecision.Decision.CREATE and existing_decision and existing_decision.decided_by_id:
        chosen = None
    elif kind == MigrationMatchDecision.Kind.NONE and not block_reasons:
        decision = MigrationMatchDecision.Decision.CREATE
        chosen = None
    else:
        decision = MigrationMatchDecision.Decision.PENDING
        chosen = None
    if decision in {MigrationMatchDecision.Decision.LINK, MigrationMatchDecision.Decision.CREATE} and kind != MigrationMatchDecision.Kind.AMBIGUOUS:
        block_reasons = [item for item in block_reasons if item.get('column') != 'match']

    fills, conflicts = ([], [])
    if chosen is not None:
        fills, conflicts = _field_diff(chosen, values)
        resolutions = (existing_decision.field_resolution if existing_decision else {}) or {}
        unresolved = [item for item in conflicts if resolutions.get(item['field']) not in {'keep', 'use_imported'}]
        if unresolved:
            block_reasons.append({
                'column': 'conflict',
                'message': 'Review fields that differ from the existing student. Existing values are kept unless you choose otherwise.',
            })
    elif decision == MigrationMatchDecision.Decision.CREATE:
        for field, label in (
            ('gender', 'Gender'),
            ('date_of_birth', 'Date of birth'),
            ('admission_date', 'Admission date'),
        ):
            present = _text(values.get(field))
            if field != 'gender':
                present = _iso_date(values.get(field))
            if not present:
                block_reasons.append({'column': field, 'message': f'{label} is required for a new student.'})
        if not first or not last:
            block_reasons.append({'column': 'full_name', 'message': 'A new student needs a first and last name.'})
    block_reasons.extend(enum_blocks)

    guardian = _plan_guardian(
        values=values,
        student=chosen,
        parents=parents,
        decision=existing_decision,
    )
    if guardian.get('blocked'):
        block_reasons.append({'column': 'guardian', 'message': guardian['message']})
    if job.template == MigrationJob.Template.STUDENT_INFORMATION:
        enrollment = _plan_current_class(
            values=values,
            streams=streams or [],
            saved=saved or {},
            active_term=active_term,
            class_memory=class_memory or {},
            stream_id=corrections.get('stream_id') or '',
        )
    else:
        enrollment = _plan_enrollment(
            values=values,
            years=years,
            year_plans=year_plans,
            active_term=active_term,
            school_id=job.school_id,
        )
    if enrollment.get('blocked'):
        block_reasons.append({'column': 'enrollment', 'message': enrollment['message']})

    proposal = {
        'action': 'link' if chosen is not None else 'create' if decision == MigrationMatchDecision.Decision.CREATE else 'review',
        'match_kind': kind,
        'match_reason': reason,
        'candidates': candidates,
        'student_id': str(chosen.id) if chosen is not None else '',
        'student_label': f'{chosen.first_name} {chosen.last_name}' if chosen is not None else f'{first} {last}'.strip(),
        'fills': fills,
        'conflicts': conflicts,
        'guardian': guardian,
        'enrollment': enrollment,
        'lifecycle': _lifecycle(values, is_new=chosen is None),
        'blocked': bool(block_reasons),
        'block_reasons': block_reasons,
        'duplicate_warning': duplicate_warning,
        'corrections': corrections,
    }
    return proposal, {
        'kind': kind,
        'decision': decision,
        'student': chosen,
        'reason': reason,
        'candidates': candidates,
    }


def _plan_guardian(*, values, student, parents, decision):
    name = _text(values.get('guardian_name'))
    raw_phone = _text(values.get('guardian_phone'))
    phone = _phone(raw_phone)
    if not name and not raw_phone:
        return {'action': 'none', 'message': ''}
    if raw_phone and not phone:
        return {
            'action': 'skipped',
            'message': 'The guardian phone is not a Ghana number, so the guardian link will be skipped.',
            'blocked': False,
        }
    if name and not phone:
        return {
            'action': 'skipped',
            'message': 'A guardian phone is required before a guardian can be linked.',
            'blocked': False,
        }
    parent = parents.get(phone)
    primary = None
    if student is not None:
        primary = next((link for link in student.parent_links.all() if link.is_primary), None)
    if parent is None:
        return {'action': 'create', 'name': name or 'Guardian', 'phone': phone, 'blocked': False}
    if primary and primary.parent_id == parent.id:
        return {'action': 'already_linked', 'name': parent.name, 'phone': phone, 'blocked': False}
    if primary and primary.parent_id != parent.id:
        choice = decision.guardian_decision if decision else ''
        if choice not in {'keep', 'add_secondary'}:
            return {
                'action': 'review',
                'name': parent.name,
                'phone': phone,
                'current_primary': primary.parent.name,
                'message': 'This student already has a different primary guardian.',
                'blocked': True,
            }
        return {
            'action': choice,
            'name': parent.name,
            'phone': phone,
            'current_primary': primary.parent.name,
            'blocked': False,
        }
    return {'action': 'reuse', 'name': parent.name, 'phone': phone, 'blocked': False}


def _plan_enrollment(*, values, years, year_plans, active_term, school_id):
    from academics.models import ClassStream

    year_label = _text(values.get('academic_year'))
    class_name = _text(values.get('class_name'))
    term_key = _normalize_term(values.get('term'))
    if not year_label and not class_name and not term_key:
        return {'action': 'none', 'blocked': False}
    if not year_label or not class_name or not term_key:
        return {
            'action': 'missing',
            'blocked': True,
            'message': 'An enrollment needs an academic year, a term, and a class. Missing history is not invented.',
        }
    current = (
        active_term is not None
        and active_term.academic_year.academic_year == year_label
        and active_term.term == term_key
    )
    year = years.get(year_label)
    plan = year_plans.get(year_label)
    if year is None and not plan:
        return {
            'action': 'needs_year',
            'label': year_label,
            'blocked': True,
            'message': f'Confirm start and end dates before creating inactive year {year_label}.',
        }
    streams = ClassStream.objects.filter(class_level__school_id=school_id).select_related(
        'class_level',
        'class_level__level',
    )
    match = next((stream for stream in streams if _key(stream.full_name) == _key(class_name)), None)
    if current:
        operational = (
            match is not None
            and match.is_active
            and not match.is_migration_snapshot
            and match.class_level.is_active
            and not match.class_level.is_migration_snapshot
            and match.class_level.level.is_active
            and not match.class_level.level.is_migration_snapshot
        )
        if not operational:
            return {
                'action': 'needs_operational_class',
                'class_name': class_name,
                'blocked': True,
                'message': f'Current-term class "{class_name}" must match a real class. A historical snapshot will not be created.',
            }
        return {
            'action': 'current',
            'class_name': class_name,
            'stream_id': str(match.id),
            'year': year_label,
            'term': term_key,
            'blocked': False,
        }
    if match is not None:
        return {
            'action': 'historical_existing',
            'class_name': class_name,
            'stream_id': str(match.id),
            'year': year_label,
            'term': term_key,
            'blocked': False,
        }
    return {
        'action': 'snapshot',
        'class_name': class_name,
        'year': year_label,
        'term': term_key,
        'blocked': False,
    }


def _plan_current_class(*, values, streams, saved, active_term, class_memory=None, stream_id=''):
    if stream_id:
        if active_term is None:
            return {
                'action': 'missing',
                'blocked': True,
                'message': 'Set the current term before importing classes.',
            }
        match = next((stream for stream in streams if str(stream.id) == str(stream_id) and is_operational(stream)), None)
        if match is None:
            return {
                'action': 'needs_operational_class',
                'blocked': True,
                'message': 'Choose a class before saving.',
            }
        return {
            'action': 'current',
            'class_name': match.full_name,
            'stream_id': str(match.id),
            'year': active_term.academic_year.academic_year,
            'term': active_term.term,
            'blocked': False,
        }
    class_name = _text(values.get('class_name'))
    stream_name = _text(values.get('stream_name'))
    if not class_name and not stream_name:
        return {'action': 'none', 'blocked': False}
    if active_term is None:
        return {
            'action': 'missing',
            'blocked': True,
            'message': 'Set the current term before importing classes.',
        }
    resolved = apply_saved(
        resolve_placement(streams, class_name, stream_name, current=True, memory=class_memory),
        saved,
        current=True,
    )
    enrollment = _enrollment_from_resolution(
        resolved,
        year=active_term.academic_year.academic_year,
        term=active_term.term,
        current=True,
    )
    explicit = _text(values.get('is_new_student'))
    if explicit:
        enrollment['is_new_student'] = _parse_bool(explicit, True)
        enrollment['is_new_student_explicit'] = True
    return enrollment


def _enrollment_from_resolution(resolved, *, year, term, current):
    status = resolved.get('status')
    enrollment = {
        'class_name': resolved.get('label') or '',
        'year': year,
        'term': term,
        'stream_id': resolved.get('stream_id') or '',
        'class_label': resolved.get('class_label') or '',
        'stream_label': resolved.get('stream_label') or '',
        'resolution_status': status,
        'message': resolved.get('message') or '',
        'source_value': resolved.get('source_value') or '',
    }
    if status in {'exact', 'confirmed', 'approved'} and resolved.get('stream_id'):
        enrollment['action'] = 'current' if current else 'historical_existing'
        enrollment['blocked'] = False
        return enrollment
    if resolved.get('use_snapshot') and not current:
        enrollment['action'] = 'snapshot'
        enrollment['blocked'] = False
        return enrollment
    enrollment['action'] = 'needs_operational_class' if current else 'unresolved'
    enrollment['blocked'] = True
    if not enrollment['message']:
        enrollment['message'] = 'Choose a class before saving.'
    return enrollment


def _plan_history_row(*, job, row, by_id, by_name_dob, by_name_phone, references, parents, years, year_plans, active_term, duplicate_ids, streams=None, saved=None, class_memory=None, enums=None):
    del by_name_dob, by_name_phone, references, parents, duplicate_ids, enums
    corrections = _corrections(row)
    values = _overlay_values(dict(row.transformed_values or {}), corrections)
    row.transformed_values = values
    student_id = _text(values.get('student_id'))
    id_students = by_id.get(student_id.casefold(), []) if student_id else []
    block_reasons = []
    kind = MigrationMatchDecision.Kind.NONE
    reason = 'Enrollment history does not create students.'
    candidates = []
    student = None
    decision = MigrationMatchDecision.Decision.PENDING
    if not student_id:
        block_reasons.append({'column': 'student_id', 'message': 'Student ID is required.'})
    elif len(id_students) == 1:
        kind = MigrationMatchDecision.Kind.EXACT
        reason = 'Exact student ID.'
        student = id_students[0]
        candidates = [_candidate(student, reason)]
        decision = MigrationMatchDecision.Decision.LINK
    elif len(id_students) > 1:
        kind = MigrationMatchDecision.Kind.AMBIGUOUS
        reason = 'More than one student has this student ID.'
        candidates = [_candidate(item, reason) for item in id_students]
        block_reasons.append({'column': 'match', 'message': reason})
    else:
        block_reasons.append({
            'column': 'student_id',
            'message': 'This student ID is not in the school. Enrollment history does not create students.',
        })
    enrollment = _plan_history_enrollment(
        values=values,
        streams=streams or [],
        saved=saved or {},
        years=years,
        year_plans=year_plans,
        active_term=active_term,
        class_memory=class_memory or {},
        stream_id=corrections.get('stream_id') or '',
    )
    if enrollment.get('blocked'):
        block_reasons.append({'column': 'enrollment', 'message': enrollment['message']})
    proposal = {
        'action': 'link' if student is not None else 'review',
        'match_kind': kind,
        'match_reason': reason,
        'candidates': candidates,
        'student_id': str(student.id) if student is not None else '',
        'student_label': f'{student.first_name} {student.last_name}' if student is not None else student_id,
        'fills': [],
        'conflicts': [],
        'guardian': {'action': 'none', 'blocked': False},
        'enrollment': enrollment,
        'lifecycle': {'apply': False, 'is_active': True, 'is_graduated': False, 'leave_reason': ''},
        'blocked': bool(block_reasons),
        'block_reasons': block_reasons,
        'duplicate_warning': '',
        'corrections': corrections,
    }
    return proposal, {
        'kind': kind,
        'decision': decision,
        'student': student,
        'reason': reason,
        'candidates': candidates,
    }


def _plan_history_enrollment(*, values, streams, saved, years, year_plans, active_term, class_memory=None, stream_id=''):
    if stream_id:
        match = next((stream for stream in streams if str(stream.id) == str(stream_id)), None)
        if match is not None:
            values = {**values, 'class_name': match.full_name, 'stream_name': ''}
    year_label = _text(values.get('academic_year'))
    class_name = _text(values.get('class_name'))
    stream_name = _text(values.get('stream_name'))
    term_key = _normalize_term(values.get('term'))
    if not year_label or not class_name or not term_key:
        return {
            'action': 'missing',
            'blocked': True,
            'message': 'An enrollment needs an academic year, a term, and a class.',
        }
    current = (
        active_term is not None
        and active_term.academic_year.academic_year == year_label
        and active_term.term == term_key
    )
    resolved = apply_saved(
        resolve_placement(streams, class_name, stream_name, current=current, memory=class_memory),
        saved,
        current=current,
    )
    if years.get(year_label) is None and not year_plans.get(year_label):
        enrollment = _enrollment_from_resolution(resolved, year=year_label, term=term_key, current=current)
        enrollment['action'] = 'needs_year'
        enrollment['label'] = year_label
        enrollment['blocked'] = True
        enrollment['message'] = f'Enter the start and end dates for {year_label}.'
        return enrollment
    return _enrollment_from_resolution(resolved, year=year_label, term=term_key, current=current)


def _lifecycle(values, *, is_new):
    active = _parse_bool(values.get('is_active'), True)
    graduated = _parse_bool(values.get('is_graduated'), False)
    status = _key(values.get('student_status') or values.get('is_graduated'))
    if status in {'yes', 'graduated', 'graduate', 'alumni', 'true', '1'}:
        graduated = True
    if status in {'left', 'inactive', 'withdrawn'}:
        active = False
    return {
        'apply': is_new,
        'is_active': active and not (_key(values.get('is_active')) in {'left', 'inactive'}),
        'is_graduated': graduated,
        'leave_reason': _text(values.get('leave_reason')),
    }


def _save_decision(row, state):
    decision, _created = MigrationMatchDecision.objects.get_or_create(
        row=row,
        defaults={
            'kind': state['kind'],
            'decision': state['decision'],
            'student': state['student'],
            'reason': state['reason'],
            'candidates': state['candidates'],
        },
    )
    if decision.decision == MigrationMatchDecision.Decision.PENDING or decision.decided_by_id is None:
        decision.kind = state['kind']
        decision.decision = state['decision']
        decision.student = state['student']
        decision.reason = state['reason']
        decision.candidates = state['candidates']
        decision.save(update_fields=['kind', 'decision', 'student', 'reason', 'candidates', 'updated_at'])


def _summarize(rows, year_plans):
    plan = {
        'new_students': 0,
        'linked_students': 0,
        'empty_fills': 0,
        'match_reviews': 0,
        'conflicts': 0,
        'guardians_reused': 0,
        'guardians_created': 0,
        'guardian_conflicts': 0,
        'historical_enrollments': 0,
        'current_enrollments': 0,
        'years_to_create': len([item for item in year_plans.values() if not item.get('exists')]),
        'snapshots': 0,
        'blocked': 0,
        'ready': 0,
    }
    for row in rows:
        proposal = row.proposal or {}
        if proposal.get('blocked') or row.validation_status == MigrationRow.ValidationStatus.BLOCKED:
            plan['blocked'] += 1
        else:
            plan['ready'] += 1
        if proposal.get('action') == 'create' and not proposal.get('blocked'):
            plan['new_students'] += 1
        if proposal.get('action') == 'link' and not proposal.get('blocked'):
            plan['linked_students'] += 1
        plan['empty_fills'] += len(proposal.get('fills') or [])
        if proposal.get('action') == 'review':
            plan['match_reviews'] += 1
        if proposal.get('conflicts'):
            plan['conflicts'] += 1
        guardian = proposal.get('guardian') or {}
        if guardian.get('action') in {'reuse', 'already_linked', 'keep', 'add_secondary'}:
            plan['guardians_reused'] += 1
        if guardian.get('action') == 'create':
            plan['guardians_created'] += 1
        if guardian.get('action') == 'review':
            plan['guardian_conflicts'] += 1
        enrollment = proposal.get('enrollment') or {}
        if enrollment.get('action') == 'current':
            plan['current_enrollments'] += 1
        if enrollment.get('action') in {'historical_existing', 'snapshot'}:
            plan['historical_enrollments'] += 1
        if enrollment.get('action') == 'snapshot':
            plan['snapshots'] += 1
    return plan
