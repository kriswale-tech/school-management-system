"""Preview opening balances. This does not write fees or payments."""

from decimal import Decimal, InvalidOperation

from fees.models import StudentFee
from migration.models import MigrationJob, MigrationMatchDecision, MigrationRow, SchoolValueMapping
from migration.services.reconciliation import apply_row_enums, canonical_year, enum_memory
from migration.services.staging import preview_summary
from migration.services.student_plan import (
    _candidate,
    _corrections,
    _index_students,
    _iso_date,
    _key,
    _normalize_term,
    _overlay_values,
    _phone,
    _student_name,
    _text,
)
from schools.models import AcademicYear, Term

MONEY = Decimal('0.01')
MAX_AMOUNT = Decimal('99999999.99')


def plan_opening_job(job):
    if job.template != MigrationJob.Template.OPENING_BALANCES:
        raise ValueError('This planner is only for opening balances.')
    school = job.school
    rows = list(
        MigrationRow.objects.filter(job=job, sheet__included=True)
        .select_related('sheet__migration_file', 'match_decision', 'match_decision__student')
        .prefetch_related('sheet__field_mappings')
        .order_by('sheet__sheet_name', 'source_row_number')
    )
    _students, by_id, by_name_dob, by_name_phone = _index_students(school)
    from migration.models import ExternalStudentReference

    references = {
        (ref.source_system, ref.external_id.casefold()): ref.student
        for ref in ExternalStudentReference.objects.filter(school=school).select_related('student')
    }
    years = {
        year.academic_year: year
        for year in AcademicYear.objects.filter(school=school).prefetch_related('terms')
    }
    year_plans = {
        item['label']: item
        for item in (job.summary or {}).get('year_plans', [])
        if item.get('label')
    }
    year_memory = {
        item.source_value: item.canonical_value
        for item in SchoolValueMapping.objects.filter(school=school, field_name='academic_year')
        if item.canonical_value
    }
    enums = enum_memory(school)
    prepared = []
    for row in rows:
        values, enum_blocks = apply_row_enums(job, row, enums)
        values = _overlay_values(values, _corrections(row))
        enum_blocks = [item for item in enum_blocks if item.get('column') not in _corrections(row)]
        row.transformed_values = values
        prepared.append((row, values, enum_blocks))

    combo_counts = {}
    for _row, values, _blocks in prepared:
        identifier = _text(values.get('student_id')) or _text(values.get('external_id'))
        if not identifier:
            continue
        combo = (identifier.casefold(), _year_key(values, year_memory), _term_key(values))
        combo_counts[combo] = combo_counts.get(combo, 0) + 1

    existing_opening = set(
        StudentFee.objects.filter(
            student__school=school,
            fee_item__is_migration_opening_balance=True,
        ).values_list('student_id', 'term_id')
    )
    ordinary_fees = set(
        StudentFee.objects.filter(
            student__school=school,
            fee_item__is_migration_opening_balance=False,
        ).values_list('student_id', 'term_id')
    )

    for row, values, enum_blocks in prepared:
        proposal = _plan_row(
            job=job,
            row=row,
            values=values,
            enum_blocks=enum_blocks,
            by_id=by_id,
            by_name_dob=by_name_dob,
            by_name_phone=by_name_phone,
            references=references,
            years=years,
            year_plans=year_plans,
            year_memory=year_memory,
            combo_counts=combo_counts,
            existing_opening=existing_opening,
            ordinary_fees=ordinary_fees,
        )
        row.proposal = proposal
        row.validation_status = (
            MigrationRow.ValidationStatus.BLOCKED
            if proposal.get('blocked')
            else MigrationRow.ValidationStatus.READY
        )
        row.errors = proposal.get('block_reasons', []) if proposal.get('blocked') else []
        row.warnings = proposal.get('warnings', [])

    if rows:
        MigrationRow.objects.bulk_update(
            rows,
            ['proposal', 'validation_status', 'errors', 'warnings', 'transformed_values', 'updated_at'],
        )
    summary = preview_summary(job)
    summary['opening'] = _opening_summary(rows)
    summary['year_plans'] = list(year_plans.values())
    summary['plan'] = {
        'ready': summary['opening']['valid_rows'],
        'blocked': summary['opening']['blocked_rows'],
        'match_reviews': summary['opening']['review_rows'],
    }
    job.summary = summary
    job.save(update_fields=['summary', 'updated_at'])
    return summary


def _year_key(values, year_memory):
    raw = _text(values.get('academic_year'))
    saved = year_memory.get(_key(raw))
    return canonical_year(saved or raw)


def _term_key(values):
    return _normalize_term(values.get('term')) or _key(values.get('term'))


def _amount(raw):
    text = _text(raw).replace(',', '').replace('GHS', '').replace('GH₵', '').replace('₵', '').strip()
    if not text:
        return None, 'Enter the outstanding balance.'
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None, 'Enter the outstanding balance as a number with up to two decimal places.'
    if value.as_tuple().exponent < -2:
        return None, 'Enter the outstanding balance as a number with up to two decimal places.'
    value = value.quantize(MONEY)
    if value < 0:
        return None, 'A negative balance cannot be imported.'
    if value > MAX_AMOUNT:
        return None, 'This amount is too large for the ledger.'
    return value, ''


def _plan_row(*, job, row, values, enum_blocks, by_id, by_name_dob, by_name_phone, references, years, year_plans, year_memory, combo_counts, existing_opening, ordinary_fees):
    block_reasons = list(enum_blocks)
    warnings = []
    student, kind, reason, candidates = _match_student(
        job=job,
        row=row,
        values=values,
        by_id=by_id,
        by_name_dob=by_name_dob,
        by_name_phone=by_name_phone,
        references=references,
    )
    if kind == 'missing':
        block_reasons.append({'column': 'student_id', 'message': 'Enter a student ID.'})
    elif kind == 'unknown':
        block_reasons.append({
            'column': 'student_id',
            'message': reason,
        })
    elif kind == 'ambiguous':
        block_reasons.append({'column': 'match', 'message': reason})
    elif kind == 'probable':
        block_reasons.append({'column': 'match', 'message': reason})

    year_label = _year_key(values, year_memory)
    term_key = _normalize_term(values.get('term'))
    year = years.get(year_label)
    enrollment = {'year': year_label, 'term': term_key, 'action': 'balance'}
    if not year_label:
        block_reasons.append({'column': 'academic_year', 'message': 'Enter the academic year.'})
    elif year is None and year_label not in year_plans:
        if _pattern_year(year_label):
            enrollment['action'] = 'needs_year'
            block_reasons.append({
                'column': 'academic_year',
                'message': f'Enter the start and end dates for {year_label}.',
            })
        else:
            block_reasons.append({
                'column': 'academic_year',
                'message': f'Choose the academic year for "{values.get("academic_year")}".',
            })
    elif year is not None and term_key and not any(term.term == term_key for term in year.terms.all()):
        block_reasons.append({
            'column': 'term',
            'message': f'{year_label} does not have this term.',
        })
    if values.get('term') and not term_key and not any(item.get('column') == 'term' for item in block_reasons):
        block_reasons.append({
            'column': 'term',
            'message': f'Choose First term, Second term, or Third term for "{values.get("term")}".',
        })

    amount, amount_error = _amount(values.get('outstanding_balance'))
    if amount_error and amount is None:
        block_reasons.append({'column': 'outstanding_balance', 'message': amount_error})
    elif amount == 0:
        warnings.append({
            'column': 'outstanding_balance',
            'message': 'A zero balance is left out.',
        })

    student_id = _text(values.get('student_id')) or _text(values.get('external_id'))
    duplicate_warning = ''
    if student_id:
        combo = (student_id.casefold(), year_label, term_key or _key(values.get('term')))
        if combo_counts.get(combo, 0) > 1:
            duplicate_warning = (
                f'{student_id} already has a row for {year_label or "this year"} '
                f'{_term_label(term_key) or "this term"} in this file.'
            )
            block_reasons.append({
                'column': 'outstanding_balance',
                'message': (
                    f'{duplicate_warning} Change one of these rows before saving. '
                    'They are not added together.'
                ),
            })

    overlap = False
    if student is not None and year is not None and term_key and kind == 'exact':
        term = next((item for item in year.terms.all() if item.term == term_key), None)
        if term is not None and (student.id, term.id) in existing_opening:
            block_reasons.append({
                'column': 'outstanding_balance',
                'message': 'This student already has an opening balance for this term. It was not changed.',
            })
        elif term is not None and (student.id, term.id) in ordinary_fees:
            overlap = True
            warnings.append({
                'column': 'outstanding_balance',
                'message': 'This student already has other fees for this term. The opening balance is added to them.',
            })

    blocked = bool(block_reasons)
    if amount == 0 and not blocked:
        action = 'skip'
    elif kind == 'probable':
        action = 'review'
    elif blocked:
        action = 'blocked'
    else:
        action = 'balance'
    first_name, last_name = _student_name(values)
    label = f'{first_name} {last_name}'.strip()
    if student is not None:
        label = f'{student.first_name} {student.last_name}'.strip()
    elif not label:
        label = _text(values.get('student_id')) or _text(values.get('external_id'))
    return {
        'action': action,
        'blocked': blocked,
        'block_reasons': block_reasons,
        'warnings': warnings,
        'amount': f'{amount:.2f}' if amount is not None else '',
        'student_pk': str(student.id) if student is not None and kind == 'exact' else '',
        'student_label': label,
        'match_kind': kind if kind in {'exact', 'probable', 'ambiguous'} else 'none',
        'match_reason': reason,
        'candidates': candidates,
        'duplicate_warning': duplicate_warning,
        'overlap': overlap,
        'enrollment': enrollment,
        'source_reference': _text(values.get('source_reference')),
        'notes': _text(values.get('notes')),
        'corrections': _corrections(row),
    }


def _pattern_year(label):
    parts = label.split('/')
    return (
        len(parts) == 2
        and all(part.isdigit() and len(part) == 4 for part in parts)
        and int(parts[1]) >= int(parts[0])
    )


def _term_label(term_key):
    return {
        'first_term': 'First term',
        'second_term': 'Second term',
        'third_term': 'Third term',
    }.get(term_key, '')


def _match_student(*, job, row, values, by_id, by_name_dob, by_name_phone, references, unknown_id='', unknown_ref=''):
    try:
        decision = row.match_decision
    except MigrationMatchDecision.DoesNotExist:
        decision = None
    if (
        decision is not None
        and decision.decision == MigrationMatchDecision.Decision.LINK
        and decision.student_id
        and decision.student.school_id == job.school_id
    ):
        student = decision.student
        return student, 'exact', 'Confirmed by an administrator.', [_candidate(student, 'Confirmed')]

    student_id = _text(values.get('student_id'))
    external_id = _text(values.get('external_id'))
    source = job.source_system or ''
    ref_student = references.get((source, external_id.casefold())) if external_id else None
    id_students = by_id.get(student_id.casefold(), []) if student_id else []
    if student_id:
        if len(id_students) == 1:
            student = id_students[0]
            return student, 'exact', 'Exact student ID.', [_candidate(student, 'Exact student ID.')]
        if len(id_students) > 1:
            return None, 'ambiguous', 'More than one student has this student ID.', [
                _candidate(item, 'Student ID') for item in id_students
            ]
        return None, 'unknown', unknown_id or 'No student has this ID. Opening balances cannot add students.', []
    if external_id:
        if ref_student is not None:
            return ref_student, 'exact', 'External student reference.', [_candidate(ref_student, 'External reference')]
        return None, 'unknown', unknown_ref or 'No student has this reference. Opening balances cannot add students.', []

    first, last = _student_name(values)
    if not (first and last):
        return None, 'missing', 'Missing student.', []
    dob = _iso_date(values.get('date_of_birth'))
    phone = _phone(values.get('guardian_phone'))
    probable = []
    probable_reason = ''
    if dob:
        probable = by_name_dob.get((_key(first), _key(last), dob), [])
        probable_reason = 'Same name and date of birth.'
    if not probable and phone:
        probable = by_name_phone.get((_key(first), _key(last), phone), [])
        probable_reason = 'Same name and guardian phone.'
    if len(probable) == 1:
        return None, 'probable', f'{probable_reason} Confirm this student.', [
            _candidate(probable[0], probable_reason),
        ]
    if len(probable) > 1:
        return None, 'ambiguous', f'{probable_reason} Several students fit.', [
            _candidate(item, probable_reason) for item in probable
        ]
    return None, 'unknown', 'Unknown student.', []


def _opening_summary(rows):
    valid_amount = Decimal('0.00')
    by_year = {}
    by_term = {}
    students = set()
    years = set()
    terms = set()
    valid_rows = 0
    blocked_rows = 0
    review_rows = 0
    skipped_rows = 0
    duplicates = 0
    overlaps = 0
    for row in rows:
        proposal = row.proposal or {}
        if proposal.get('action') == 'review':
            review_rows += 1
        if proposal.get('blocked'):
            blocked_rows += 1
        if proposal.get('duplicate_warning'):
            duplicates += 1
        if proposal.get('overlap'):
            overlaps += 1
        if proposal.get('action') == 'skip':
            skipped_rows += 1
        if proposal.get('action') != 'balance':
            continue
        amount = Decimal(proposal.get('amount') or '0')
        valid_rows += 1
        valid_amount += amount
        year = (proposal.get('enrollment') or {}).get('year') or ''
        term = (proposal.get('enrollment') or {}).get('term') or ''
        if proposal.get('student_pk'):
            students.add(proposal['student_pk'])
        if year:
            years.add(year)
            by_year[year] = by_year.get(year, Decimal('0.00')) + amount
        if year or term:
            terms.add(f'{year} {term}'.strip())
            key = (year, term)
            by_term[key] = by_term.get(key, Decimal('0.00')) + amount
    return {
        'total_rows': len(rows),
        'valid_rows': valid_rows,
        'blocked_rows': blocked_rows,
        'review_rows': review_rows,
        'skipped_rows': skipped_rows,
        'unique_students': len(students),
        'academic_years': sorted(years),
        'terms': sorted(terms),
        'by_year': [
            {'academic_year': year, 'total': f'{amount:.2f}'}
            for year, amount in sorted(by_year.items())
        ],
        'by_term': [
            {'academic_year': year, 'term': term, 'total': f'{amount:.2f}'}
            for (year, term), amount in sorted(by_term.items())
        ],
        'total': f'{valid_amount:.2f}',
        'duplicates': duplicates,
        'overlaps': overlaps,
    }


def resolved_term(school, year_label, term_key):
    return Term.objects.filter(
        school=school,
        academic_year__academic_year=year_label,
        term=term_key,
    ).select_related('academic_year').first()
