from collections import Counter
from types import SimpleNamespace

from migration.models import FieldMapping, MigrationJob, MigrationRow
from migration.services.transforms import STEPS, TransformError
from migration.services.mapping import _suggested_transforms
from migration.targets import DATE_FIELDS, fields_for

NAME_FIELDS = frozenset({'first_name', 'last_name', 'other_names'})


def sheet_mappings(sheet):
    rows = list(
        FieldMapping.objects.filter(sheet=sheet)
        .prefetch_related('transforms')
        .order_by('position')
    )
    if rows:
        return rows
    if sheet.mapping_profile_id:
        return list(
            FieldMapping.objects.filter(profile=sheet.mapping_profile)
            .prefetch_related('transforms')
            .order_by('position')
        )
    return []


def _apply_mapping(raw_values, mapping, *, automatic_enums=True):
    errors = []
    warnings = []
    produced = {}
    source = raw_values.get(mapping.source_column, '')
    current = source
    steps = list(mapping.transforms.all())
    if not steps and mapping.target_field and not mapping.ignored:
        steps = [
            SimpleNamespace(step=item['step'], config=item['config'])
            for item in _suggested_transforms(mapping.target_field)
            if automatic_enums or item['step'] != 'value_map'
        ]
    for step in steps:
        handler = STEPS[step.step]
        try:
            if step.step == 'combine':
                current = handler(raw_values, step.config)
            else:
                current = handler(current, step.config)
        except TransformError as exc:
            bucket = errors if exc.blocked else warnings
            bucket.append({'column': mapping.source_column, 'message': str(exc)})
            if exc.blocked:
                return produced, errors, warnings
            current = ''
        if step.step == 'split_name' and isinstance(current, dict):
            produced.update(current)
            current = source
    if mapping.ignored or not mapping.target_field:
        return produced, errors, warnings
    if mapping.target_field not in produced:
        produced[mapping.target_field] = current if not isinstance(current, dict) else source
    return produced, errors, warnings


def transform_row(raw_values, mappings, *, automatic_enums=True):
    transformed = {}
    errors = []
    warnings = []
    for mapping in mappings:
        produced, row_errors, row_warnings = _apply_mapping(
            raw_values,
            mapping,
            automatic_enums=automatic_enums,
        )
        transformed.update(produced)
        errors.extend(row_errors)
        warnings.extend(row_warnings)
    return transformed, errors, warnings


def _required_targets(job_type, template='', role=''):
    return [key for key, _label, required in fields_for(job_type, template, role) if required]


def validate_transformed(*, job_type, transformed, errors, warnings, template='', role=''):
    if template in {
        MigrationJob.Template.ENROLLMENT_HISTORY,
        MigrationJob.Template.OPENING_BALANCES,
        MigrationJob.Template.HISTORICAL_FINANCE,
    }:
        for field in _required_targets(job_type, template, role):
            if not str(transformed.get(field) or '').strip():
                errors.append({'column': field, 'message': f'{field.replace("_", " ").title()} is required.'})
        return errors, warnings
    if job_type == MigrationJob.JobType.STUDENT_ENROLLMENT:
        has_name = bool(transformed.get('first_name') and transformed.get('last_name'))
        if not has_name:
            errors.append({
                'column': 'full_name',
                'message': 'Map first and last name, or split a full name. The last word is suggested as the surname.',
            })
        for field in _required_targets(job_type, template):
            if field in NAME_FIELDS:
                continue
            if not str(transformed.get(field) or '').strip():
                errors.append({'column': field, 'message': f'{field.replace("_", " ").title()} is required.'})
        gender = str(transformed.get('gender') or '').strip().lower()
        if not template and gender and gender not in {'male', 'female', 'other'}:
            errors.append({
                'column': 'gender',
                'message': 'Map gender to male, female, or other.',
            })
    elif job_type == MigrationJob.JobType.FEE_FINANCIAL_HISTORY:
        if not transformed.get('student_id') and not transformed.get('full_name'):
            errors.append({
                'column': 'student_id',
                'message': 'Map a student ID or a student name so the row can be matched later.',
            })
    for field in DATE_FIELDS:
        if field in transformed and transformed[field] == '':
            continue
    return errors, warnings


def stage_sheet(sheet):
    mappings = sheet_mappings(sheet)
    job = sheet.migration_file.job
    rows = list(sheet.rows.order_by('source_row_number'))
    transformed_rows = []
    for row in rows:
        if row.commit_status == MigrationRow.CommitStatus.COMMITTED:
            transformed_rows.append(row)
            continue
        transformed, errors, warnings = transform_row(
            row.raw_values,
            mappings,
            automatic_enums=not job.template,
        )
        transformed, errors = apply_saved_corrections(row, transformed, errors, mappings)
        errors, warnings = validate_transformed(
            job_type=job.job_type,
            transformed=transformed,
            errors=errors,
            warnings=warnings,
            template=job.template,
            role=sheet.migration_file.role,
        )
        row.transformed_values = transformed
        row.errors = errors
        row.warnings = warnings
        row.validation_status = (
            MigrationRow.ValidationStatus.BLOCKED if errors else MigrationRow.ValidationStatus.READY
        )
        transformed_rows.append(row)
    if job.template != MigrationJob.Template.HISTORICAL_FINANCE:
        _mark_duplicate_ids(transformed_rows)
    MigrationRow.objects.bulk_update(
        transformed_rows,
        ['transformed_values', 'errors', 'warnings', 'validation_status', 'updated_at'],
    )
    job.status = MigrationJob.Status.PREVIEW_READY
    job.summary = preview_summary(job)
    job.save(update_fields=['status', 'summary', 'updated_at'])
    return job.summary


def _mark_duplicate_ids(rows):
    counts = Counter(
        str(row.transformed_values.get('student_id') or '').strip()
        for row in rows
        if str(row.transformed_values.get('student_id') or '').strip()
    )
    for row in rows:
        student_id = str(row.transformed_values.get('student_id') or '').strip()
        if student_id and counts[student_id] > 1:
            warning = {
                'column': 'student_id',
                'message': f'Student ID {student_id} appears more than once in this job.',
            }
            if warning not in row.warnings:
                row.warnings = [*row.warnings, warning]


def apply_saved_corrections(row, transformed, errors, mappings):
    corrections = (row.proposal or {}).get('corrections') or {}
    if not corrections:
        return transformed, errors
    for key, value in corrections.items():
        if key == 'stream_id' or value in (None, ''):
            continue
        transformed[key] = value
    targets = set(corrections)
    source_targets = {
        mapping.source_column: mapping.target_field
        for mapping in mappings
        if getattr(mapping, 'target_field', '')
    }
    kept = []
    for error in errors:
        column = error.get('column')
        target = source_targets.get(column, column)
        if target in targets or column in targets:
            continue
        kept.append(error)
    return transformed, kept


def retransform_row(row):
    mappings = sheet_mappings(row.sheet)
    job = row.sheet.migration_file.job
    transformed, errors, warnings = transform_row(
        row.raw_values,
        mappings,
        automatic_enums=not job.template,
    )
    transformed, errors = apply_saved_corrections(row, transformed, errors, mappings)
    errors, warnings = validate_transformed(
        job_type=job.job_type,
        transformed=transformed,
        errors=errors,
        warnings=warnings,
        template=job.template,
        role=row.sheet.migration_file.role,
    )
    row.transformed_values = transformed
    row.errors = errors
    row.warnings = warnings
    row.validation_status = (
        MigrationRow.ValidationStatus.BLOCKED if errors else MigrationRow.ValidationStatus.READY
    )
    row.save(update_fields=['transformed_values', 'errors', 'warnings', 'validation_status', 'updated_at'])
    return row


def preview_summary(job):
    rows = MigrationRow.objects.filter(job=job, sheet__included=True)
    unmapped = []
    for sheet in job.files.prefetch_related('sheets__field_mappings'):
        for sheet_row in sheet.sheets.all():
            if not sheet_row.included:
                continue
            mapped = {
                item.source_column
                for item in sheet_row.field_mappings.all()
                if not item.ignored and item.target_field
            }
            for header in sheet_row.detected_headers:
                if header not in mapped:
                    unmapped.append({'sheet': sheet_row.sheet_name, 'column': header})
    return {
        'total_rows': rows.count(),
        'ready_rows': rows.filter(validation_status=MigrationRow.ValidationStatus.READY).count(),
        'blocked_rows': rows.filter(validation_status=MigrationRow.ValidationStatus.BLOCKED).count(),
        'warning_rows': rows.exclude(warnings=[]).count(),
        'unmapped_columns': unmapped,
    }
