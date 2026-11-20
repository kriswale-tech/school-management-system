import csv
import hashlib
import io
import uuid
import zipfile
from datetime import date, datetime

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from openpyxl.utils.exceptions import InvalidFileException
from rest_framework.exceptions import ValidationError

from migration.models import ClassValueResolution, MigrationFile, MigrationJob, MigrationRow, MigrationSheet
from migration.services.audit import record_migration_audit
from migration.storage import get_migration_storage

CSV_DELIMITERS = ',;\t'


def _extension(filename: str) -> str:
    name = (filename or '').lower().strip()
    if '.' not in name:
        return ''
    return name.rsplit('.', 1)[-1]


def file_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _cell_text(value):
    if value is None:
        return ''
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _reject(migration_file, message):
    migration_file.status = MigrationFile.Status.REJECTED
    migration_file.error = message
    migration_file.retention_until = timezone.now() + settings.MIGRATION_FAILED_FILE_TTL
    migration_file.save(update_fields=['status', 'error', 'retention_until', 'updated_at'])


def decode_csv(content: bytes):
    if content.startswith(b'\xef\xbb\xbf'):
        return content.decode('utf-8-sig'), 'utf-8-sig'
    for encoding in ('utf-8', 'cp1252'):
        try:
            return content.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ValidationError({'file': 'The CSV encoding is not UTF-8 or Windows-1252.'})


def detect_delimiter(text: str) -> str:
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=CSV_DELIMITERS)
    except csv.Error:
        return ','
    delimiter = dialect.delimiter
    if delimiter not in CSV_DELIMITERS:
        return ','
    return delimiter


def _rows_from_matrix(matrix, header_row):
    if header_row < 1 or header_row > len(matrix):
        raise ValidationError({'header_row': 'The header row is outside the sheet.'})
    header_cells = matrix[header_row - 1]
    headers = []
    seen = {}
    for index, cell in enumerate(header_cells):
        label = _cell_text(cell).strip()
        if not label:
            label = f'Column {index + 1}'
        count = seen.get(label, 0) + 1
        seen[label] = count
        headers.append(label if count == 1 else f'{label} ({count})')
    data = []
    for offset, raw in enumerate(matrix[header_row:], start=header_row + 1):
        if not any(_cell_text(cell).strip() for cell in raw):
            continue
        values = {}
        for index, header in enumerate(headers):
            cell = raw[index] if index < len(raw) else ''
            values[header] = _cell_text(cell)
        data.append((offset, values))
    return headers, data


def first_nonempty_row(matrix) -> int:
    for index, row in enumerate(matrix, start=1):
        if any(_cell_text(cell).strip() for cell in row):
            return index
    return 1


def parse_xlsx(content: bytes):
    from openpyxl import load_workbook

    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except (InvalidFileException, zipfile.BadZipFile, OSError, KeyError, ValueError) as exc:
        raise ValidationError({
            'file': 'This Excel file could not be opened. It may be damaged or password-protected.',
        }) from exc
    sheets = []
    try:
        for worksheet in workbook.worksheets:
            matrix = []
            for row in worksheet.iter_rows(values_only=True):
                matrix.append(list(row))
                if len(matrix) > settings.MIGRATION_MAX_ROWS + 5:
                    raise ValidationError({
                        'file': f'A worksheet exceeds {settings.MIGRATION_MAX_ROWS} rows.',
                    })
            sheets.append((worksheet.title, matrix))
    finally:
        workbook.close()
    if not sheets:
        raise ValidationError({'file': 'The workbook has no worksheets.'})
    return sheets


def parse_csv(content: bytes):
    text, encoding = decode_csv(content)
    delimiter = detect_delimiter(text)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    matrix = []
    for row in reader:
        matrix.append(row)
        if len(matrix) > settings.MIGRATION_MAX_ROWS + 5:
            raise ValidationError({
                'file': f'The CSV exceeds {settings.MIGRATION_MAX_ROWS} rows.',
            })
    if not matrix:
        raise ValidationError({'file': 'The CSV file is empty.'})
    return encoding, delimiter, matrix


def release_stored_file(job):
    """Drop the spreadsheet once the import is saved. The import record stays."""
    storage = get_migration_storage()
    for migration_file in job.files.all():
        if not migration_file.storage_key:
            continue
        try:
            storage.delete(migration_file.storage_key)
        except OSError:
            pass
        migration_file.storage_key = ''
        migration_file.save(update_fields=['storage_key', 'updated_at'])


def _replace_existing_file(job, role=''):
    existing = list(job.files.all())
    if role:
        existing = [item for item in existing if item.role == role]
    if not existing:
        return
    saved = job.status in {
        MigrationJob.Status.COMMITTING,
        MigrationJob.Status.PARTIALLY_COMMITTED,
        MigrationJob.Status.COMMITTED,
    } or MigrationRow.objects.filter(
        job=job,
        commit_status=MigrationRow.CommitStatus.COMMITTED,
    ).exists()
    if saved:
        raise ValidationError({'file': 'Records from this import have been saved, so the file cannot be replaced.'})
    storage = get_migration_storage()
    for migration_file in existing:
        if migration_file.storage_key:
            try:
                storage.delete(migration_file.storage_key)
            except OSError:
                pass
        migration_file.delete()
    if not role:
        ClassValueResolution.objects.filter(job=job).delete()
    job.file_hash = ''
    job.summary = {}
    job.status = MigrationJob.Status.UPLOADED if job.files.exists() else MigrationJob.Status.DRAFT
    job.save(update_fields=['file_hash', 'summary', 'status', 'updated_at'])


def store_upload(*, job, uploaded_by, filename, content, content_type, role=''):
    extension = _extension(filename)
    if extension not in {'xlsx', 'csv'}:
        raise ValidationError({'file': 'Upload an Excel .xlsx file or a .csv file.'})
    if not content:
        raise ValidationError({'file': 'The file is empty.'})
    if len(content) > settings.MIGRATION_MAX_FILE_SIZE:
        raise ValidationError({'file': 'The file is larger than the migration size limit.'})
    if job.template == MigrationJob.Template.HISTORICAL_FINANCE:
        if role not in {'charges', 'payments'}:
            raise ValidationError({'role': 'Choose the charges file or the payments file.'})
    else:
        role = ''
    _replace_existing_file(job, role)

    digest = file_sha256(content)
    if MigrationFile.objects.filter(job=job, file_hash=digest).exists():
        raise ValidationError({'file': 'This file is already attached to the job.'})

    storage = get_migration_storage()
    key = f'{job.school_id}/{job.id}/{uuid.uuid4().hex}.{extension}'
    storage.save(key, ContentFile(content))

    migration_file = MigrationFile.objects.create(
        job=job,
        original_filename=filename or f'upload.{extension}',
        storage_key=key,
        file_hash=digest,
        file_size=len(content),
        content_type=content_type or '',
        uploaded_by=uploaded_by,
        status=MigrationFile.Status.INSPECTING,
        role=role,
    )
    if not job.file_hash:
        job.file_hash = digest
        job.save(update_fields=['file_hash', 'updated_at'])
    record_migration_audit(
        school=job.school,
        job=job,
        actor=uploaded_by,
        action='upload',
        summary=f'Uploaded {migration_file.original_filename}.',
        payload={'file_id': str(migration_file.id), 'file_hash': digest},
    )
    return migration_file


def inspect_migration_file(file_id):
    migration_file = (
        MigrationFile.objects.select_related('job', 'job__school')
        .filter(pk=file_id)
        .first()
    )
    if migration_file is None:
        return
    storage = get_migration_storage()
    try:
        with storage.open(migration_file.storage_key, 'rb') as handle:
            content = handle.read()
    except FileNotFoundError:
        _reject(migration_file, 'The uploaded file could not be read back from storage.')
        return

    extension = _extension(migration_file.original_filename)
    try:
        if extension == 'xlsx':
            parsed = parse_xlsx(content)
            encoding = ''
            delimiter = ''
            sheet_payloads = parsed
        else:
            encoding, delimiter, matrix = parse_csv(content)
            sheet_payloads = [('CSV', matrix)]
    except ValidationError as exc:
        detail = exc.detail
        if isinstance(detail, dict):
            message = ' '.join(str(item) for values in detail.values() for item in (values if isinstance(values, list) else [values]))
        else:
            message = str(detail)
        _reject(migration_file, message)
        return

    migration_file.sheets.all().delete()
    sample_limit = settings.MIGRATION_SAMPLE_ROWS
    created = 0
    for sheet_name, matrix in sheet_payloads:
        if not any(_cell_text(cell).strip() for row in matrix for cell in row):
            continue
        header_row = first_nonempty_row(matrix)
        try:
            headers, data = _rows_from_matrix(matrix, header_row=header_row)
        except ValidationError as exc:
            _reject(migration_file, str(exc.detail))
            return
        if len(data) > settings.MIGRATION_MAX_ROWS:
            _reject(migration_file, f'A worksheet exceeds {settings.MIGRATION_MAX_ROWS} rows.')
            return
        sheet = MigrationSheet.objects.create(
            migration_file=migration_file,
            sheet_name=sheet_name[:200],
            header_row=header_row,
            detected_headers=headers,
            sample_rows=[values for _, values in data[:sample_limit]],
            row_count=len(data),
            included=True,
        )
        MigrationRow.objects.bulk_create([
            MigrationRow(
                job=migration_file.job,
                sheet=sheet,
                source_row_number=number,
                raw_values=values,
            )
            for number, values in data
        ])
        created += 1
    if created == 0:
        _reject(migration_file, 'The file has no rows to import.')
        return

    migration_file.detected_encoding = encoding
    migration_file.detected_delimiter = delimiter
    migration_file.status = MigrationFile.Status.READY
    migration_file.error = ''
    migration_file.save(update_fields=[
        'detected_encoding',
        'detected_delimiter',
        'status',
        'error',
        'updated_at',
    ])
    job = migration_file.job
    if job.status == MigrationJob.Status.DRAFT:
        job.status = MigrationJob.Status.UPLOADED
        job.save(update_fields=['status', 'updated_at'])
    record_migration_audit(
        school=job.school,
        job=job,
        actor=migration_file.uploaded_by,
        action='inspect',
        summary=f'Inspected {migration_file.original_filename}.',
        payload={'file_id': str(migration_file.id), 'sheets': migration_file.sheets.count()},
    )


def restage_sheet_header(*, sheet, header_row):
    storage = get_migration_storage()
    migration_file = sheet.migration_file
    with storage.open(migration_file.storage_key, 'rb') as handle:
        content = handle.read()
    extension = _extension(migration_file.original_filename)
    if extension == 'xlsx':
        sheets = parse_xlsx(content)
        matrix = next((rows for name, rows in sheets if name == sheet.sheet_name), None)
    else:
        _, _, matrix = parse_csv(content)
    if matrix is None:
        raise ValidationError({'sheet': 'That worksheet is no longer in the file.'})
    headers, data = _rows_from_matrix(matrix, header_row)
    if len(data) > settings.MIGRATION_MAX_ROWS:
        raise ValidationError({'file': f'A worksheet exceeds {settings.MIGRATION_MAX_ROWS} rows.'})
    sheet.rows.all().delete()
    sheet.header_row = header_row
    sheet.detected_headers = headers
    sheet.sample_rows = [values for _, values in data[:settings.MIGRATION_SAMPLE_ROWS]]
    sheet.row_count = len(data)
    sheet.save(update_fields=[
        'header_row',
        'detected_headers',
        'sample_rows',
        'row_count',
        'updated_at',
    ])
    MigrationRow.objects.bulk_create([
        MigrationRow(
            job=migration_file.job,
            sheet=sheet,
            source_row_number=number,
            raw_values=values,
        )
        for number, values in data
    ])
    return sheet
