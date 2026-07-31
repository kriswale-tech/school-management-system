import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone as datetime_timezone
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from shared.helpers import format_phone_number
from shared.services.spreadsheets import (
    build_csv_bytes,
    normalize_cell,
    parse_csv_rows,
    parse_xlsx_rows,
)
from students.bulk_template import (
    FAILURE_EXTRA_HEADERS,
    IMPORT_HEADERS,
    build_student_failure_xlsx,
)
from students.models import ClassEnrollment, Student, StudentParent
from students.services import (
    _get_or_create_parent,
    generate_student_id,
    get_active_term,
)

IMPORT_COLUMNS = set(IMPORT_HEADERS)
SUPPORTED_UPLOAD_FORMATS = {'xlsx', 'csv'}


@dataclass
class ParsedStudentBulkRow:
    row_number: int
    first_name: str = ''
    last_name: str = ''
    other_names: str = ''
    gender: str = ''
    date_of_birth: str = ''
    admission_date: str = ''
    is_new_student: str = ''
    class_name: str = ''
    guardian_name: str = ''
    guardian_phone: str = ''
    guardian_email: str = ''
    guardian_relationship: str = ''

    def as_dict(self) -> dict:
        return {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'other_names': self.other_names,
            'gender': self.gender,
            'date_of_birth': self.date_of_birth,
            'admission_date': self.admission_date,
            'is_new_student': self.is_new_student,
            'class_name': self.class_name,
            'guardian_name': self.guardian_name,
            'guardian_phone': self.guardian_phone,
            'guardian_email': self.guardian_email,
            'guardian_relationship': self.guardian_relationship,
        }

    def has_guardian_data(self) -> bool:
        return any([
            self.guardian_name,
            self.guardian_phone,
            self.guardian_email,
            self.guardian_relationship,
        ])


@dataclass
class StudentBulkRowResult:
    row_number: int
    status: str
    messages: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)


@dataclass
class StudentBulkImportSummary:
    rows_total: int = 0
    rows_valid: int = 0
    rows_with_errors: int = 0
    rows_with_warnings: int = 0
    rows_processed: int = 0
    rows_succeeded: int = 0
    rows_failed: int = 0
    students_to_create: int = 0
    students_created: int = 0
    guardians_to_link: int = 0
    guardians_linked: int = 0


@dataclass
class StudentBulkFailureExport:
    token: str
    download_url: str
    expires_at: timezone.datetime
    format: str


@dataclass
class StudentBulkImportResult:
    dry_run: bool
    summary: StudentBulkImportSummary
    rows: list[StudentBulkRowResult] = field(default_factory=list)
    failures: StudentBulkFailureExport | None = None


def detect_upload_format(filename: str, content_type: str | None = None) -> str:
    lowered = (filename or '').lower()
    if lowered.endswith('.xlsx'):
        return 'xlsx'
    if lowered.endswith('.csv'):
        return 'csv'
    if content_type == 'text/csv':
        return 'csv'
    if content_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
        return 'xlsx'
    raise ValidationError({'file': 'Upload a .xlsx or .csv file.'})


def parse_student_bulk_upload(file_bytes: bytes, *, upload_format: str) -> list[ParsedStudentBulkRow]:
    if upload_format == 'xlsx':
        raw_rows = parse_xlsx_rows(file_bytes, allowed_columns=IMPORT_COLUMNS)
    else:
        raw_rows = parse_csv_rows(file_bytes, allowed_columns=IMPORT_COLUMNS)

    if len(raw_rows) > settings.STUDENT_BULK_IMPORT_MAX_ROWS:
        raise ValidationError({
            'file': (
                f'Import exceeds the maximum of {settings.STUDENT_BULK_IMPORT_MAX_ROWS} rows.'
            ),
        })

    return [_to_parsed_row(raw_row) for raw_row in raw_rows]


def preview_student_bulk_import(school, rows: list[ParsedStudentBulkRow]) -> StudentBulkImportResult:
    from students.bulk_reference import build_student_bulk_reference_context

    context = build_student_bulk_reference_context(school)
    summary = StudentBulkImportSummary(rows_total=len(rows))
    results: list[StudentBulkRowResult] = []

    for row in rows:
        messages = _validate_row(context, row)
        if any(message.startswith('ERROR:') for message in messages):
            status = 'error'
            summary.rows_with_errors += 1
        elif messages:
            status = 'warning'
            summary.rows_with_warnings += 1
            summary.students_to_create += 1
            if row.has_guardian_data():
                summary.guardians_to_link += 1
        else:
            status = 'valid'
            summary.rows_valid += 1
            summary.students_to_create += 1
            if row.has_guardian_data():
                summary.guardians_to_link += 1

        results.append(
            StudentBulkRowResult(
                row_number=row.row_number,
                status=status,
                messages=[
                    message.replace('ERROR: ', '').replace('WARN: ', '')
                    for message in messages
                ],
                data=row.as_dict(),
            ),
        )

    return StudentBulkImportResult(dry_run=True, summary=summary, rows=results)


@transaction.atomic
def commit_student_bulk_import(
    school,
    rows: list[ParsedStudentBulkRow],
    *,
    upload_format: str,
) -> StudentBulkImportResult:
    from students.bulk_reference import build_student_bulk_reference_context

    context = build_student_bulk_reference_context(school)
    term = get_active_term(school)
    summary = StudentBulkImportSummary(rows_total=len(rows), rows_processed=len(rows))
    failed_rows: list[dict] = []

    for row in rows:
        messages: list[str] = []
        try:
            with transaction.atomic():
                validated = _validate_row(context, row)
                error_messages = [m for m in validated if m.startswith('ERROR:')]
                if error_messages:
                    messages.extend(m.replace('ERROR: ', '') for m in error_messages)
                    raise ValidationError({'detail': messages[-1]})

                _create_student_from_row(
                    school=school,
                    term=term,
                    context=context,
                    row=row,
                    summary=summary,
                )
        except ValidationError as exc:
            detail = exc.detail
            if isinstance(detail, dict):
                for value in detail.values():
                    if isinstance(value, list):
                        messages.extend(str(item) for item in value)
                    else:
                        messages.append(str(value))
            elif isinstance(detail, list):
                messages.extend(str(item) for item in detail)
            else:
                messages.append(str(detail))
        except Exception as exc:  # noqa: BLE001 — capture row failures without aborting batch
            messages.append(str(exc))

        if messages:
            summary.rows_failed += 1
            failed_row = row.as_dict()
            failed_row['row_number'] = row.row_number
            failed_row['failure_reason'] = '; '.join(messages)
            failed_rows.append(failed_row)
        else:
            summary.rows_succeeded += 1

    failures = None
    if failed_rows:
        failures = _write_failure_export(school, failed_rows, upload_format=upload_format)

    return StudentBulkImportResult(
        dry_run=False,
        summary=summary,
        failures=failures,
    )


def get_failure_export_path(school_id, token: str, upload_format: str) -> Path:
    return (
        settings.BULK_IMPORT_LOCAL_MEDIA_ROOT
        / 'students'
        / str(school_id)
        / f'{token}.{upload_format}'
    )


def load_failure_export(school_id, token: str) -> tuple[Path, str]:
    for upload_format in SUPPORTED_UPLOAD_FORMATS:
        path = get_failure_export_path(school_id, token, upload_format)
        if not path.exists():
            continue
        if _is_failure_export_expired(path):
            path.unlink(missing_ok=True)
            break
        return path, upload_format
    raise ValidationError({'detail': 'Failure export not found or expired.'})


def _to_parsed_row(raw_row: dict) -> ParsedStudentBulkRow:
    return ParsedStudentBulkRow(
        row_number=int(raw_row.get('row_number') or 0),
        first_name=normalize_cell(raw_row.get('first_name')),
        last_name=normalize_cell(raw_row.get('last_name')),
        other_names=normalize_cell(raw_row.get('other_names')),
        gender=normalize_cell(raw_row.get('gender')).lower(),
        date_of_birth=normalize_cell(raw_row.get('date_of_birth')),
        admission_date=normalize_cell(raw_row.get('admission_date')),
        is_new_student=normalize_cell(raw_row.get('is_new_student')).lower(),
        class_name=normalize_cell(raw_row.get('class_name')),
        guardian_name=normalize_cell(raw_row.get('guardian_name')),
        guardian_phone=normalize_cell(raw_row.get('guardian_phone')),
        guardian_email=normalize_cell(raw_row.get('guardian_email')),
        guardian_relationship=normalize_cell(raw_row.get('guardian_relationship')).lower(),
    )


def _validate_row(context, row: ParsedStudentBulkRow) -> list[str]:
    messages: list[str] = []

    if not row.first_name:
        messages.append('ERROR: first_name is required.')
    if not row.last_name:
        messages.append('ERROR: last_name is required.')

    gender_values = {choice.value for choice in Student.GenderChoices}
    if not row.gender:
        messages.append('ERROR: gender is required.')
    elif row.gender not in gender_values:
        messages.append(f'ERROR: gender must be one of: {", ".join(sorted(gender_values))}.')

    dob = _parse_date(row.date_of_birth)
    if not row.date_of_birth:
        messages.append('ERROR: date_of_birth is required.')
    elif dob is None:
        messages.append('ERROR: date_of_birth must be a valid date (YYYY-MM-DD).')

    admission = _parse_date(row.admission_date)
    if not row.admission_date:
        messages.append('ERROR: admission_date is required.')
    elif admission is None:
        messages.append('ERROR: admission_date must be a valid date (YYYY-MM-DD).')

    _, is_new_error = _parse_bool(row.is_new_student, default=False)
    if is_new_error:
        messages.append(f'ERROR: {is_new_error}')

    _, stream_error = context.resolve_stream(row.class_name)
    if stream_error:
        messages.append(f'ERROR: {stream_error}')

    if row.has_guardian_data():
        if not row.guardian_name:
            messages.append('ERROR: guardian_name is required when guardian fields are provided.')
        if not row.guardian_phone:
            messages.append('ERROR: guardian_phone is required when guardian fields are provided.')
        else:
            try:
                format_phone_number(row.guardian_phone)
            except ValueError as exc:
                messages.append(f'ERROR: {exc}')

        relationship_values = {choice.value for choice in StudentParent.RelationshipChoices}
        if not row.guardian_relationship:
            messages.append(
                'ERROR: guardian_relationship is required when guardian fields are provided.',
            )
        elif row.guardian_relationship not in relationship_values:
            messages.append(
                'ERROR: guardian_relationship must be one of: '
                f'{", ".join(sorted(relationship_values))}.',
            )

        if row.guardian_email:
            if '@' not in row.guardian_email or '.' not in row.guardian_email.split('@')[-1]:
                messages.append('ERROR: guardian_email is invalid.')

    return messages


def _create_student_from_row(*, school, term, context, row: ParsedStudentBulkRow, summary):
    stream, stream_error = context.resolve_stream(row.class_name)
    if stream_error or stream is None:
        raise ValidationError({'class_name': stream_error or 'Class not found.'})

    is_new_student, is_new_error = _parse_bool(row.is_new_student, default=False)
    if is_new_error:
        raise ValidationError({'is_new_student': is_new_error})

    dob = _parse_date(row.date_of_birth)
    admission = _parse_date(row.admission_date)
    if dob is None or admission is None:
        raise ValidationError({'detail': 'Invalid date values.'})

    student = Student.objects.create(
        school=school,
        student_id=generate_student_id(school=school),
        first_name=row.first_name.strip(),
        last_name=row.last_name.strip(),
        other_names=(row.other_names or '').strip(),
        gender=row.gender,
        date_of_birth=dob,
        admission_date=admission,
    )

    if row.has_guardian_data():
        parent = _get_or_create_parent(
            school=school,
            guardian={
                'name': row.guardian_name,
                'phone_number': row.guardian_phone,
                'email': row.guardian_email,
            },
        )
        StudentParent.objects.create(
            student=student,
            parent=parent,
            relationship=row.guardian_relationship,
            is_primary=True,
        )
        summary.guardians_linked += 1

    ClassEnrollment.objects.create(
        student=student,
        term=term,
        stream=stream,
        is_new_student=is_new_student,
    )
    summary.students_created += 1


def _parse_date(value: str) -> date | None:
    if not value:
        return None

    cleaned = value.strip()
    if ' ' in cleaned and cleaned[4:5] == '-':
        cleaned = cleaned[:10]

    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue

    try:
        return date.fromisoformat(cleaned[:10])
    except ValueError:
        return None


def _parse_bool(value: str, *, default: bool = False) -> tuple[bool, str | None]:
    if not value:
        return default, None
    normalized = value.strip().lower()
    if normalized in {'1', 'true', 'yes', 'y'}:
        return True, None
    if normalized in {'0', 'false', 'no', 'n'}:
        return False, None
    return default, 'is_new_student must be true or false.'


def _write_failure_export(
    school,
    failed_rows: list[dict],
    *,
    upload_format: str,
) -> StudentBulkFailureExport:
    headers = [*IMPORT_HEADERS, *FAILURE_EXTRA_HEADERS]
    token = str(uuid.uuid4())
    expires_at = timezone.now() + settings.STUDENT_BULK_IMPORT_FAILURE_TTL
    path = get_failure_export_path(school.id, token, upload_format)
    path.parent.mkdir(parents=True, exist_ok=True)

    if upload_format == 'xlsx':
        payload = build_student_failure_xlsx(school, failed_rows)
    else:
        payload = build_csv_bytes(headers=headers, rows=failed_rows)

    path.write_bytes(payload)
    return StudentBulkFailureExport(
        token=token,
        download_url=f'/api/v1/students/bulk-upload/failures/{token}/',
        expires_at=expires_at,
        format=upload_format,
    )


def _is_failure_export_expired(path: Path) -> bool:
    modified_at = timezone.datetime.fromtimestamp(
        path.stat().st_mtime,
        tz=datetime_timezone.utc,
    )
    return timezone.now() - modified_at > settings.STUDENT_BULK_IMPORT_FAILURE_TTL
