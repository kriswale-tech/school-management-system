"""Row-level corrections on the review step. Raw file values stay unchanged."""

import csv
import io

from rest_framework.exceptions import ValidationError

from academics.models import ClassStream
from migration.models import MigrationJob, MigrationRow
from migration.services.audit import record_migration_audit
from migration.services.class_resolution import (
    apply_saved,
    is_operational,
    load_class_memory,
    load_streams,
    resolve_placement,
    saved_map,
)
from migration.services.reconciliation import ENUMS, enum_memory, resolve_enum
from migration.services.staging import retransform_row
from migration.services.student_plan import TERM_ALIASES, _key, plan_for_job
from migration.services.transforms import parse_date, TransformError
from migration.targets import fields_for

DATE_FIELDS = ('date_of_birth', 'admission_date', 'enrollment_date', 'payment_date')
SKIPPED_FIELDS = {'full_name', 'stream_name', 'class_name'}
TERM_OPTIONS = (
    ('first_term', 'First'),
    ('second_term', 'Second'),
    ('third_term', 'Third'),
)


def _reasons(row):
    proposal = row.proposal or {}
    return proposal.get('block_reasons') or proposal.get('reasons') or row.errors or []


def _field_keys(job, row):
    if job.template in {
        MigrationJob.Template.OPENING_BALANCES,
        MigrationJob.Template.HISTORICAL_FINANCE,
    }:
        role = row.sheet.migration_file.role if job.template == MigrationJob.Template.HISTORICAL_FINANCE else ''
        return [
            key for key, _label, _required in fields_for(job.job_type, job.template, role)
            if key != 'full_name'
        ]
    keys = []
    for key, _label, _required in fields_for(job.job_type, job.template):
        if key in SKIPPED_FIELDS:
            if key == 'class_name' and 'stream_id' not in keys:
                keys.append('stream_id')
            continue
        if key not in keys:
            keys.append(key)
    if 'stream_id' not in keys:
        keys.append('stream_id')
    return keys


def _current_value(row, key):
    corrections = (row.proposal or {}).get('corrections') or {}
    if key in corrections:
        return corrections[key]
    return (row.transformed_values or {}).get(key, '')


def _labels(job, row=None):
    role = ''
    if row is not None and job.template == MigrationJob.Template.HISTORICAL_FINANCE:
        role = row.sheet.migration_file.role
    labels = {key: label for key, label, _required in fields_for(job.job_type, job.template, role)}
    labels['stream_id'] = 'Class'
    return labels


def _display_enum(row, key, spec, memory):
    current = str(_current_value(row, key) or '')
    if not current or current == '__omit__':
        return ''
    saved = memory.get((key, _key(current)))
    status, canonical, _origin = resolve_enum(spec, current, saved)
    allowed = {value for value, _label in spec['options']}
    if status == 'omitted' or canonical not in allowed:
        return ''
    return canonical


def _display_date(row, key):
    current = str(_current_value(row, key) or '').strip()
    if not current:
        return ''
    try:
        return parse_date(current, {'format': '%d/%m/%Y'})
    except TransformError:
        return ''


def _display_term(row):
    current = str(_current_value(row, 'term') or '')
    canonical = TERM_ALIASES.get(_key(current), '')
    allowed = {value for value, _label in TERM_OPTIONS}
    if canonical in allowed:
        return canonical
    return current if current in allowed else ''


def _display_stream(row, streams):
    options = {str(stream.id) for stream in streams}
    current = str(_current_value(row, 'stream_id') or (row.proposal or {}).get('enrollment', {}).get('stream_id') or '')
    if current in options:
        return current
    values = row.transformed_values or {}
    class_name = str(values.get('class_name') or '')
    stream_name = str(values.get('stream_name') or '')
    for stream in streams:
        same_class = _key(stream.class_level.name) == _key(class_name)
        same_stream = _key(stream.name) == _key(stream_name)
        if _key(stream.full_name) == _key(class_name) or (same_class and same_stream and class_name):
            return str(stream.id)
    current_term = row.job.template != MigrationJob.Template.ENROLLMENT_HISTORY
    resolved = apply_saved(
        resolve_placement(
            streams,
            class_name,
            stream_name,
            current=current_term,
            memory=load_class_memory(row.job.school),
        ),
        saved_map(row.job),
        current=current_term,
    )
    stream_id = str(resolved.get('stream_id') or '')
    return stream_id if stream_id in options else ''


def correction_form(row):
    job = row.job
    labels = _labels(job, row)
    memory = enum_memory(job.school)
    fields = []
    for key in _field_keys(job, row):
        if key == 'stream_id':
            streams = load_streams(job.school_id)
            if job.template == MigrationJob.Template.STUDENT_INFORMATION:
                streams = [stream for stream in streams if is_operational(stream)]
            fields.append({
                'key': key,
                'label': labels[key],
                'kind': 'select',
                'value': _display_stream(row, streams),
                'options': [{'value': str(stream.id), 'label': stream.full_name} for stream in streams],
            })
            continue
        if key in ENUMS:
            spec = ENUMS[key]
            fields.append({
                'key': key,
                'label': spec['label'],
                'kind': 'select',
                'value': _display_enum(row, key, spec, memory),
                'options': [{'value': value, 'label': label} for value, label in spec['options']],
            })
            continue
        if key == 'term':
            fields.append({
                'key': key,
                'label': labels[key],
                'kind': 'select',
                'value': _display_term(row),
                'options': [{'value': value, 'label': label} for value, label in TERM_OPTIONS],
            })
            continue
        fields.append({
            'key': key,
            'label': labels[key],
            'kind': 'date' if key in DATE_FIELDS else 'text',
            'value': _display_date(row, key) if key in DATE_FIELDS else str(_current_value(row, key) or ''),
            'options': [],
        })
    return {'reasons': _reasons(row), 'fields': fields}


def _clean_values(job, incoming, row=None):
    if not isinstance(incoming, dict) or not incoming:
        raise ValidationError({'values': 'Enter the corrected values.'})
    cleaned = {}
    for key, raw in incoming.items():
        value = str(raw or '').strip()
        if not value:
            continue
        if key in DATE_FIELDS:
            try:
                cleaned[key] = parse_date(value, {'format': '%d/%m/%Y'})
            except TransformError as exc:
                raise ValidationError({key: str(exc)}) from exc
            continue
        if key in ENUMS:
            allowed = {option for option, _label in ENUMS[key]['options']}
            if value not in allowed:
                raise ValidationError({key: 'Choose one of the listed values.'})
            cleaned[key] = value
            continue
        if key == 'term':
            canonical = TERM_ALIASES.get(_key(value), '')
            if not canonical:
                raise ValidationError({'term': 'Choose First, Second, or Third.'})
            cleaned[key] = canonical
            continue
        if key == 'stream_id':
            stream = (
                ClassStream.objects.filter(pk=value, class_level__school=job.school)
                .select_related('class_level', 'class_level__level')
                .first()
            )
            if stream is None:
                raise ValidationError({'stream_id': 'Choose a class from this school.'})
            if job.template == MigrationJob.Template.STUDENT_INFORMATION and not is_operational(stream):
                raise ValidationError({'stream_id': 'Choose a current class.'})
            cleaned['stream_id'] = str(stream.id)
            cleaned['class_name'] = stream.full_name
            continue
        role = ''
        if row is not None and job.template == MigrationJob.Template.HISTORICAL_FINANCE:
            role = row.sheet.migration_file.role
        allowed_text = {
            field
            for field, _label, _required in fields_for(job.job_type, job.template, role)
            if field not in SKIPPED_FIELDS and field not in DATE_FIELDS and field not in ENUMS and field != 'term'
        }
        if key in allowed_text:
            cleaned[key] = value
            continue
        raise ValidationError({key: 'That field cannot be edited here.'})
    if not cleaned:
        raise ValidationError({'values': 'Enter the corrected values.'})
    return cleaned


def apply_row_correction(*, row, actor, values):
    if row.commit_status == MigrationRow.CommitStatus.COMMITTED:
        raise ValidationError({'row': 'This row has already been saved.'})
    cleaned = _clean_values(row.job, values, row)
    proposal = dict(row.proposal or {})
    proposal['corrections'] = {**(proposal.get('corrections') or {}), **cleaned}
    row.proposal = proposal
    row.save(update_fields=['proposal', 'updated_at'])
    retransform_row(row)
    summary = plan_for_job(row.job)
    record_migration_audit(
        school=row.job.school,
        job=row.job,
        actor=actor,
        action='mapping',
        summary=f'Corrected row {row.source_row_number}.',
        payload={'row_id': str(row.id), 'fields': sorted(cleaned)},
    )
    row.refresh_from_db()
    return summary


IMPORT_NAMES = {
    'student_information': 'Student information',
    'enrollment_history': 'Enrollment history',
    'opening_balances': 'Opening balances',
    'historical_finance': 'Fee history',
}


def attention_filename(job):
    name = IMPORT_NAMES.get(job.template, 'Students')
    source = str(job.source_system or '').strip()
    if source:
        name = f'{name} - {source}'
    safe = ''.join(' ' if char in '\\/:*?"<>|' else char for char in name).strip()
    return f'{safe} needs-attention.csv'


def attention_csv(job):
    if job.template == MigrationJob.Template.HISTORICAL_FINANCE:
        seen = {}
        for role in ('charges', 'payments'):
            for key, label, _required in fields_for(job.job_type, job.template, role):
                seen.setdefault(key, label)
        columns = list(seen.items())
    else:
        columns = [(key, label) for key, label, _required in fields_for(job.job_type, job.template)]
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['Sheet', 'Row', 'Reason', *[label for _key, label in columns]])
    rows = (
        MigrationRow.objects.filter(job=job, sheet__included=True)
        .select_related('sheet')
        .order_by('sheet__sheet_name', 'source_row_number')
    )
    for row in rows:
        proposal = row.proposal or {}
        blocked = row.validation_status != MigrationRow.ValidationStatus.READY or proposal.get('blocked')
        if not blocked:
            continue
        values = row.transformed_values or {}
        reason = ' '.join(item.get('message', '') for item in _reasons(row) if item.get('message'))
        writer.writerow([
            row.sheet.sheet_name,
            row.source_row_number,
            reason,
            *[values.get(key, '') for key, _label in columns],
        ])
    return buffer.getvalue()
