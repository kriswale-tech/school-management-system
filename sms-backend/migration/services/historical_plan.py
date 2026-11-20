"""Preview historical charges and payments. This does not write the ledger."""

from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation

from fees.models import StudentFee
from migration.models import (
    ExternalStudentReference,
    MigrationHistoricalCharge,
    MigrationHistoricalPayment,
    MigrationJob,
    MigrationOpeningBalance,
    MigrationRow,
    SchoolValueMapping,
)
from migration.services.opening_plan import (
    _match_student,
    _pattern_year,
    _term_label,
)
from migration.services.reconciliation import apply_row_enums, canonical_year, enum_memory
from migration.services.staging import preview_summary
from migration.services.student_plan import (
    _corrections,
    _index_students,
    _key,
    _normalize_term,
    _overlay_values,
    _student_name,
    _text,
)
from migration.services.transforms import TransformError, parse_date
from schools.models import AcademicYear

MONEY = Decimal('0.01')
MAX_AMOUNT = Decimal('99999999.99')
UNKNOWN_ID = 'No student has this ID. Fee history cannot add students.'
UNKNOWN_REF = 'No student has this reference. Fee history cannot add students.'


def plan_historical_job(job):
    if job.template != MigrationJob.Template.HISTORICAL_FINANCE:
        raise ValueError('This planner is only for fee history.')
    school = job.school
    rows = list(
        MigrationRow.objects.filter(job=job, sheet__included=True)
        .select_related(
            'sheet__migration_file',
            'match_decision',
            'match_decision__student',
        )
        .prefetch_related('sheet__field_mappings')
        .order_by('sheet__sheet_name', 'source_row_number')
    )
    _students, by_id, by_name_dob, by_name_phone = _index_students(school)
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
    opening = set(
        MigrationOpeningBalance.objects.filter(school=school).values_list('student_id', 'term_id')
    )
    existing_charges = {
        (student_id, term_id, fee_name)
        for student_id, term_id, fee_name in MigrationHistoricalCharge.objects.filter(
            school=school,
        ).values_list('student_id', 'term_id', 'fee_name')
    }
    existing_payments = set(
        MigrationHistoricalPayment.objects.filter(school=school).values_list('reference_key', flat=True)
    )
    prepared = []
    for row in rows:
        values, enum_blocks = apply_row_enums(job, row, enums)
        values = _overlay_values(values, _corrections(row))
        corrected = set(_corrections(row))
        enum_blocks = [item for item in enum_blocks if item.get('column') not in corrected]
        row.transformed_values = values
        prepared.append((row, values, enum_blocks))

    charge_counts = defaultdict(int)
    for row, values, _blocks in prepared:
        if row.sheet.migration_file.role != 'charges':
            continue
        fee_name = _fee_key(values.get('fee_item'))
        identifier = _text(values.get('student_id')) or _text(values.get('external_id'))
        if not identifier or not fee_name:
            continue
        combo = (identifier.casefold(), _year_key(values, year_memory), _term_key(values), fee_name)
        charge_counts[combo] += 1

    proposals = []
    for row, values, enum_blocks in prepared:
        role = row.sheet.migration_file.role
        if role == 'payments':
            proposal = _plan_payment_row(
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
                opening=opening,
                existing_payments=existing_payments,
            )
        else:
            proposal = _plan_charge_row(
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
                charge_counts=charge_counts,
                opening=opening,
                existing_charges=existing_charges,
            )
        proposal['corrections'] = _corrections(row)
        proposals.append((row, proposal))

    _block_payment_groups(proposals)
    for row, proposal in proposals:
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
    summary['history'] = _history_summary(rows)
    summary['year_plans'] = list(year_plans.values())
    summary['plan'] = {
        'ready': summary['history']['valid_rows'],
        'blocked': summary['history']['blocked_rows'],
        'match_reviews': summary['history']['review_rows'],
    }
    job.summary = summary
    job.save(update_fields=['summary', 'updated_at'])
    return summary


def _year_key(values, year_memory):
    raw = _text(values.get('academic_year'))
    saved = year_memory.get(_key(raw))
    return canonical_year(saved or raw)


def _term_key(values):
    return _normalize_term(values.get('term')) or ''


def _fee_key(raw):
    return ' '.join(_text(raw).casefold().split())


def _amount(raw, label):
    text = _text(raw).replace(',', '').replace('GHS', '').replace('GH₵', '').replace('₵', '').strip()
    if not text:
        return None, f'Enter the {label}.'
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None, f'Enter the {label} as a number with up to two decimal places.'
    if value.as_tuple().exponent < -2:
        return None, f'Enter the {label} as a number with up to two decimal places.'
    value = value.quantize(MONEY)
    if value < 0:
        return None, 'A negative amount cannot be imported.'
    if value > MAX_AMOUNT:
        return None, 'This amount is too large for the ledger.'
    return value, ''


def _payment_day(raw):
    text = _text(raw)
    if not text:
        return None, 'Enter the payment date.'
    if len(text) >= 10 and text[4:5] == '-' and text[7:8] == '-':
        try:
            return datetime.strptime(text[:10], '%Y-%m-%d').date(), ''
        except ValueError:
            pass
    try:
        parsed = parse_date(text, {'format': '%d/%m/%Y'})
    except TransformError:
        parsed = ''
    if parsed:
        return datetime.strptime(parsed, '%Y-%m-%d').date(), ''
    return None, 'Enter the payment date as 2020-01-15 or 15/01/2020.'


def _student_context(*, job, row, values, by_id, by_name_dob, by_name_phone, references):
    block_reasons = []
    student, kind, reason, candidates = _match_student(
        job=job,
        row=row,
        values=values,
        by_id=by_id,
        by_name_dob=by_name_dob,
        by_name_phone=by_name_phone,
        references=references,
        unknown_id=UNKNOWN_ID,
        unknown_ref=UNKNOWN_REF,
    )
    if kind == 'missing':
        block_reasons.append({'column': 'student_id', 'message': 'Enter a student ID.'})
    elif kind in {'unknown', 'ambiguous', 'probable'}:
        block_reasons.append({'column': 'student_id' if kind == 'unknown' else 'match', 'message': reason})
    first_name, last_name = _student_name(values)
    label = f'{first_name} {last_name}'.strip()
    if student is not None:
        label = f'{student.first_name} {student.last_name}'.strip()
    elif not label:
        label = _text(values.get('student_id')) or _text(values.get('external_id'))
    return student, kind, reason, candidates, label, block_reasons


def _year_term(*, values, years, year_plans, year_memory, block_reasons):
    year_label = _year_key(values, year_memory)
    term_key = _term_key(values)
    year = years.get(year_label)
    enrollment = {'year': year_label, 'term': term_key, 'action': 'history'}
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
        block_reasons.append({'column': 'term', 'message': f'{year_label} does not have this term.'})
    if values.get('term') and not term_key and not any(item.get('column') == 'term' for item in block_reasons):
        block_reasons.append({
            'column': 'term',
            'message': f'Choose First term, Second term, or Third term for "{values.get("term")}".',
        })
    term = None
    if year is not None and term_key:
        term = next((item for item in year.terms.all() if item.term == term_key), None)
    return year_label, term_key, term, enrollment


def _plan_charge_row(*, job, row, values, enum_blocks, by_id, by_name_dob, by_name_phone, references, years, year_plans, year_memory, charge_counts, opening, existing_charges):
    block_reasons = list(enum_blocks)
    warnings = []
    student, kind, reason, candidates, label, student_blocks = _student_context(
        job=job,
        row=row,
        values=values,
        by_id=by_id,
        by_name_dob=by_name_dob,
        by_name_phone=by_name_phone,
        references=references,
    )
    block_reasons.extend(student_blocks)
    year_label, term_key, term, enrollment = _year_term(
        values=values,
        years=years,
        year_plans=year_plans,
        year_memory=year_memory,
        block_reasons=block_reasons,
    )
    fee_label = _text(values.get('fee_item'))
    fee_name = _fee_key(fee_label)
    if not fee_name:
        block_reasons.append({'column': 'fee_item', 'message': 'Enter the fee item.'})
    amount, amount_error = _amount(values.get('amount'), 'amount')
    if amount_error and amount is None:
        block_reasons.append({'column': 'amount', 'message': amount_error})
    elif amount == 0:
        warnings.append({'column': 'amount', 'message': 'A zero charge is left out.'})
    identifier = _text(values.get('student_id')) or _text(values.get('external_id'))
    if identifier and fee_name:
        combo = (identifier.casefold(), year_label, term_key, fee_name)
        if charge_counts.get(combo, 0) > 1:
            block_reasons.append({
                'column': 'fee_item',
                'message': (
                    f'{identifier} already has {fee_label} for {year_label or "this year"} '
                    f'{_term_label(term_key) or "this term"} in this file. '
                    'They are not added together.'
                ),
            })
    if student is not None and term is not None and kind == 'exact':
        if (student.id, term.id) in opening or StudentFee.objects.filter(
            student=student,
            term=term,
            fee_item__is_migration_opening_balance=True,
        ).exists():
            block_reasons.append({
                'column': 'amount',
                'message': 'This term already has an opening balance. These charges were left out.',
            })
        elif fee_name and (student.id, term.id, fee_name) in existing_charges:
            block_reasons.append({
                'column': 'fee_item',
                'message': 'This fee line was already imported. It was not changed.',
            })
    blocked = bool(block_reasons)
    if amount == 0 and not blocked:
        action = 'skip'
    elif kind == 'probable':
        action = 'review'
    elif blocked:
        action = 'blocked'
    else:
        action = 'charge'
    return _proposal(
        action=action,
        blocked=blocked,
        block_reasons=block_reasons,
        warnings=warnings,
        amount=amount,
        student=student if kind == 'exact' else None,
        label=label,
        kind=kind,
        reason=reason,
        candidates=candidates,
        enrollment=enrollment,
        extra={
            'role': 'charges',
            'fee_name': fee_name,
            'fee_label': fee_label,
            'source_reference': _text(values.get('source_reference')),
            'notes': _text(values.get('notes')),
        },
    )


def _plan_payment_row(*, job, row, values, enum_blocks, by_id, by_name_dob, by_name_phone, references, years, year_plans, year_memory, opening, existing_payments):
    block_reasons = list(enum_blocks)
    warnings = []
    student, kind, reason, candidates, label, student_blocks = _student_context(
        job=job,
        row=row,
        values=values,
        by_id=by_id,
        by_name_dob=by_name_dob,
        by_name_phone=by_name_phone,
        references=references,
    )
    block_reasons.extend(student_blocks)
    year_label, term_key, term, enrollment = _year_term(
        values=values,
        years=years,
        year_plans=year_plans,
        year_memory=year_memory,
        block_reasons=block_reasons,
    )
    reference = _text(values.get('payment_reference'))
    reference_key = reference.casefold()
    if not reference_key:
        block_reasons.append({'column': 'payment_reference', 'message': 'Enter the payment reference.'})
    paid_on, date_error = _payment_day(values.get('payment_date'))
    if date_error:
        block_reasons.append({'column': 'payment_date', 'message': date_error})
    amount, amount_error = _amount(values.get('amount'), 'amount')
    if amount_error and amount is None:
        block_reasons.append({'column': 'amount', 'message': amount_error})
    elif amount == 0:
        block_reasons.append({'column': 'amount', 'message': 'A payment amount must be greater than zero.'})
    payment_type = _text(values.get('payment_type')) or 'ordinary'
    if payment_type not in {'ordinary', 'advance'}:
        block_reasons.append({
            'column': 'payment_type',
            'message': f'Choose Ordinary or Advance for "{values.get("payment_type")}".',
        })
    method = _text(values.get('payment_method'))
    if method not in {'cash', 'cheque', 'bank_transfer', 'mobile_money', 'other'}:
        block_reasons.append({
            'column': 'payment_method',
            'message': f'Choose a payment method for "{values.get("payment_method") or method}".',
        })
    if student is not None and term is not None and kind == 'exact' and (student.id, term.id) in opening:
        block_reasons.append({
            'column': 'amount',
            'message': 'This term already has an opening balance. These payments were left out.',
        })
    if reference_key and reference_key in existing_payments:
        block_reasons.append({
            'column': 'payment_reference',
            'message': 'This payment reference was already imported. It was not changed.',
        })
    blocked = bool(block_reasons)
    if kind == 'probable' and not blocked:
        action = 'review'
    elif blocked:
        action = 'blocked'
    elif payment_type == 'advance':
        action = 'advance'
    else:
        action = 'payment'
    return _proposal(
        action=action,
        blocked=blocked,
        block_reasons=block_reasons,
        warnings=warnings,
        amount=amount,
        student=student if kind == 'exact' else None,
        label=label,
        kind=kind,
        reason=reason,
        candidates=candidates,
        enrollment=enrollment,
        extra={
            'role': 'payments',
            'payment_reference': reference,
            'reference_key': reference_key,
            'paid_on': paid_on.isoformat() if paid_on else '',
            'payment_method': method,
            'payment_type': payment_type,
            'legacy_receipt_number': _text(values.get('legacy_receipt_number')),
            'notes': _text(values.get('notes')),
        },
    )


def _block_payment_groups(proposals):
    groups = defaultdict(list)
    for row, proposal in proposals:
        if proposal.get('role') != 'payments' or not proposal.get('reference_key'):
            continue
        groups[proposal['reference_key']].append((row, proposal))
    for members in groups.values():
        signatures = {
            (
                proposal.get('student_pk'),
                proposal.get('paid_on'),
                proposal.get('payment_method'),
                proposal.get('legacy_receipt_number'),
                proposal.get('payment_type'),
            )
            for _row, proposal in members
        }
        terms = [
            (proposal.get('enrollment') or {}).get('year'),
            (proposal.get('enrollment') or {}).get('term'),
        ]
        term_keys = [
            ((proposal.get('enrollment') or {}).get('year'), (proposal.get('enrollment') or {}).get('term'))
            for _row, proposal in members
        ]
        duplicate_term = len(term_keys) != len(set(term_keys))
        mixed_advance = any(proposal.get('payment_type') == 'advance' for _row, proposal in members) and len(members) > 1
        if len(members) < 2:
            continue
        conflict = len(signatures) > 1 or duplicate_term or mixed_advance
        any_blocked = any(proposal.get('blocked') for _row, proposal in members)
        if not conflict and not any_blocked:
            continue
        if len(signatures) > 1:
            message = 'These rows use one payment reference but the student, date, method, receipt, or type does not match. The payment was left out.'
        elif duplicate_term:
            message = 'This payment is listed twice for the same term. It was left out.'
        elif mixed_advance:
            message = 'An advance uses one row. This reference was left out.'
        else:
            message = 'This payment has another row that needs attention, so it was left out.'
        for _row, proposal in members:
            if any(item.get('message') == message for item in proposal.get('block_reasons', [])):
                continue
            proposal['block_reasons'] = [*proposal.get('block_reasons', []), {'column': 'payment_reference', 'message': message}]
            proposal['blocked'] = True
            proposal['action'] = 'blocked'
        del terms


def _proposal(*, action, blocked, block_reasons, warnings, amount, student, label, kind, reason, candidates, enrollment, extra):
    payload = {
        'action': action,
        'blocked': blocked,
        'block_reasons': block_reasons,
        'warnings': warnings,
        'amount': f'{amount:.2f}' if amount is not None else '',
        'student_pk': str(student.id) if student is not None else '',
        'student_label': label,
        'match_kind': kind if kind in {'exact', 'probable', 'ambiguous'} else 'none',
        'match_reason': reason,
        'candidates': candidates,
        'enrollment': enrollment,
        'corrections': {},
    }
    payload.update(extra)
    return payload


def _history_summary(rows):
    charge_total = Decimal('0.00')
    payment_total = Decimal('0.00')
    advance_total = Decimal('0.00')
    valid_rows = blocked_rows = review_rows = skipped_rows = 0
    students = set()
    seen_payments = set()
    for row in rows:
        proposal = row.proposal or {}
        action = proposal.get('action')
        if action == 'skip':
            skipped_rows += 1
            continue
        if proposal.get('blocked') or row.validation_status == MigrationRow.ValidationStatus.BLOCKED:
            blocked_rows += 1
            if action == 'review':
                review_rows += 1
            continue
        valid_rows += 1
        if proposal.get('student_pk'):
            students.add(proposal['student_pk'])
        amount = Decimal(proposal.get('amount') or '0')
        if action == 'charge':
            charge_total += amount
        elif action == 'advance':
            advance_total += amount
        elif action == 'payment':
            key = proposal.get('reference_key')
            if key not in seen_payments:
                seen_payments.add(key)
            payment_total += amount
    return {
        'total_rows': len(rows),
        'valid_rows': valid_rows,
        'blocked_rows': blocked_rows,
        'review_rows': review_rows,
        'skipped_rows': skipped_rows,
        'unique_students': len(students),
        'charge_total': f'{charge_total:.2f}',
        'payment_total': f'{payment_total:.2f}',
        'advance_total': f'{advance_total:.2f}',
        'payments': len(seen_payments),
    }
