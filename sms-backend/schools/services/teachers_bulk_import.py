import uuid
from dataclasses import dataclass, field
from datetime import timezone as datetime_timezone
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.models import Profile, User
from shared.helpers import format_phone_number
from shared.services.spreadsheets import (
    build_csv_bytes,
    normalize_cell,
    parse_csv_rows,
    parse_xlsx_rows,
)
from schools.services.teachers_bulk_template import (
    FAILURE_EXTRA_HEADERS,
    IMPORT_HEADERS,
    build_teacher_failure_xlsx,
)
from teachers.models import ClassTeacher, TeachingAssignment

IMPORT_COLUMNS = set(IMPORT_HEADERS)

ASSIGNMENT_TYPE_CLASS_TEACHER = 'class_teacher'
ASSIGNMENT_TYPE_TEACHING = 'teaching'
SUPPORTED_UPLOAD_FORMATS = {'xlsx', 'csv'}


@dataclass
class ParsedTeacherBulkRow:
    row_number: int
    first_name: str = ''
    last_name: str = ''
    phone_number: str = ''
    email: str = ''
    assignment_type: str = ''
    class_name: str = ''
    subject_name: str = ''
    stream_name: str = ''
    subject_group_name: str = ''

    def as_dict(self) -> dict:
        return {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone_number': self.phone_number,
            'email': self.email,
            'assignment_type': self.assignment_type,
            'class_name': self.class_name,
            'subject_name': self.subject_name,
            'stream_name': self.stream_name,
            'subject_group_name': self.subject_group_name,
        }


@dataclass
class TeacherBulkRowResult:
    row_number: int
    status: str
    messages: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)


@dataclass
class TeacherBulkImportSummary:
    rows_total: int = 0
    rows_valid: int = 0
    rows_with_errors: int = 0
    rows_with_warnings: int = 0
    rows_processed: int = 0
    rows_succeeded: int = 0
    rows_failed: int = 0
    teachers_to_create: int = 0
    teachers_to_update: int = 0
    assignments_to_create: int = 0
    assignments_to_replace: int = 0
    teachers_created: int = 0
    teachers_updated: int = 0
    assignments_created: int = 0
    assignments_replaced: int = 0


@dataclass
class TeacherBulkFailureExport:
    token: str
    download_url: str
    expires_at: timezone.datetime
    format: str


@dataclass
class TeacherBulkImportResult:
    dry_run: bool
    summary: TeacherBulkImportSummary
    rows: list[TeacherBulkRowResult] = field(default_factory=list)
    failures: TeacherBulkFailureExport | None = None


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


def parse_teacher_bulk_upload(file_bytes: bytes, *, upload_format: str) -> list[ParsedTeacherBulkRow]:
    if upload_format == 'xlsx':
        raw_rows = parse_xlsx_rows(file_bytes, allowed_columns=IMPORT_COLUMNS)
    else:
        raw_rows = parse_csv_rows(file_bytes, allowed_columns=IMPORT_COLUMNS)

    if len(raw_rows) > settings.TEACHER_BULK_IMPORT_MAX_ROWS:
        raise ValidationError({
            'file': (
                f'Import exceeds the maximum of {settings.TEACHER_BULK_IMPORT_MAX_ROWS} rows.'
            ),
        })

    return [_to_parsed_row(raw_row) for raw_row in raw_rows]


def preview_teacher_bulk_import(school, rows: list[ParsedTeacherBulkRow]) -> TeacherBulkImportResult:
    from schools.services.teachers_bulk_reference import build_teacher_bulk_reference_context

    context = build_teacher_bulk_reference_context(school)
    existing_phones = _load_existing_teacher_phones(school)
    summary = TeacherBulkImportSummary(rows_total=len(rows))
    results: list[TeacherBulkRowResult] = []

    for row in rows:
        messages: list[str] = []
        teacher_action = _resolve_teacher_action(row, school, existing_phones, messages)
        assignment_action, assignment_messages = _resolve_assignment_action(context, row)
        messages.extend(assignment_messages)

        if any(message.startswith('ERROR:') for message in messages):
            status = 'error'
            summary.rows_with_errors += 1
        elif messages:
            status = 'warning'
            summary.rows_with_warnings += 1
        else:
            status = 'valid'
            summary.rows_valid += 1

        if teacher_action == 'create':
            summary.teachers_to_create += 1
        elif teacher_action == 'update':
            summary.teachers_to_update += 1

        if assignment_action == 'create':
            summary.assignments_to_create += 1
        elif assignment_action == 'replace':
            summary.assignments_to_replace += 1

        results.append(
            TeacherBulkRowResult(
                row_number=row.row_number,
                status=status,
                messages=[
                    message.replace('ERROR: ', '').replace('WARN: ', '')
                    for message in messages
                ],
                data=row.as_dict(),
            ),
        )

    return TeacherBulkImportResult(dry_run=True, summary=summary, rows=results)


@transaction.atomic
def commit_teacher_bulk_import(
    school,
    rows: list[ParsedTeacherBulkRow],
    *,
    upload_format: str,
) -> TeacherBulkImportResult:
    from schools.services.teachers_bulk_reference import build_teacher_bulk_reference_context

    context = build_teacher_bulk_reference_context(school)
    existing_phones = _load_existing_teacher_phones(school)
    summary = TeacherBulkImportSummary(rows_total=len(rows), rows_processed=len(rows))
    failed_rows: list[dict] = []
    teacher_cache: dict[str, User] = {}

    for row in rows:
        messages: list[str] = []
        try:
            teacher = _upsert_teacher(
                school,
                row,
                existing_phones=existing_phones,
                teacher_cache=teacher_cache,
                summary=summary,
                messages=messages,
            )
            assignment_created, assignment_replaced = _apply_assignment(
                context,
                teacher,
                row,
                messages=messages,
            )
            if assignment_created:
                summary.assignments_created += 1
            if assignment_replaced:
                summary.assignments_replaced += 1
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

    return TeacherBulkImportResult(
        dry_run=False,
        summary=summary,
        failures=failures,
    )


def get_failure_export_path(school_id, token: str, upload_format: str) -> Path:
    return (
        settings.BULK_IMPORT_LOCAL_MEDIA_ROOT
        / 'teachers'
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


def _to_parsed_row(raw_row: dict) -> ParsedTeacherBulkRow:
    return ParsedTeacherBulkRow(
        row_number=int(raw_row.get('row_number') or 0),
        first_name=normalize_cell(raw_row.get('first_name')),
        last_name=normalize_cell(raw_row.get('last_name')),
        phone_number=normalize_cell(raw_row.get('phone_number')),
        email=normalize_cell(raw_row.get('email')),
        assignment_type=normalize_cell(raw_row.get('assignment_type')).lower(),
        class_name=normalize_cell(raw_row.get('class_name')),
        subject_name=normalize_cell(raw_row.get('subject_name')),
        stream_name=normalize_cell(raw_row.get('stream_name')),
        subject_group_name=normalize_cell(raw_row.get('subject_group_name')),
    )


def _load_existing_teacher_phones(school) -> dict[str, User]:
    return {
        user.phone_number: user
        for user in User.objects.filter(
            school=school,
            role=User.RoleChoices.TEACHER,
        )
    }


def _resolve_teacher_action(
    row: ParsedTeacherBulkRow,
    school,
    existing_phones: dict[str, User],
    messages: list[str],
) -> str | None:
    if not row.first_name:
        messages.append('ERROR: first_name is required.')
    if not row.last_name:
        messages.append('ERROR: last_name is required.')
    if not row.phone_number:
        messages.append('ERROR: phone_number is required.')
        return None

    try:
        phone = format_phone_number(row.phone_number)
    except ValueError as exc:
        messages.append(f'ERROR: {exc}')
        return None

    existing = User.objects.filter(phone_number=phone).first()
    if existing:
        if existing.role != User.RoleChoices.TEACHER:
            messages.append('ERROR: Phone number belongs to a non-teacher account.')
            return None
        if existing.school_id != school.id:
            messages.append('ERROR: Phone number belongs to another school.')
            return None
        return 'update'

    if phone in existing_phones:
        return 'update'
    return 'create'


def _resolve_assignment_action(context, row: ParsedTeacherBulkRow) -> tuple[str | None, list[str]]:
    messages: list[str] = []
    if not row.assignment_type:
        return None, messages

    if row.assignment_type not in {ASSIGNMENT_TYPE_CLASS_TEACHER, ASSIGNMENT_TYPE_TEACHING}:
        messages.append('ERROR: assignment_type must be class_teacher or teaching.')
        return None, messages

    if not row.class_name:
        messages.append('ERROR: class_name is required when assignment_type is provided.')
        return None, messages

    class_level, class_error = context.resolve_class_level(row.class_name)
    if class_error:
        messages.append(f'ERROR: {class_error}')
        return None, messages

    stream, stream_error = context.resolve_stream(class_level, row.stream_name or None)
    if stream_error:
        messages.append(f'ERROR: {stream_error}')
        return None, messages

    if row.assignment_type == ASSIGNMENT_TYPE_CLASS_TEACHER:
        if row.subject_name:
            messages.append('WARN: subject_name is ignored for class_teacher assignments.')
        if row.subject_group_name:
            messages.append('WARN: subject_group_name is ignored for class_teacher assignments.')

        existing = ClassTeacher.objects.filter(
            class_level=class_level,
            term_id=context.term_id,
            stream=stream,
        ).first()
        if existing:
            messages.append(
                f'WARN: Will replace existing class teacher for {class_level.name}.',
            )
            return 'replace', messages
        return 'create', messages

    if not row.subject_name:
        messages.append('ERROR: subject_name is required for teaching assignments.')
        return None, messages

    class_subject, subject_error = context.resolve_class_subject(
        row.class_name,
        row.subject_name,
    )
    if subject_error:
        messages.append(f'ERROR: {subject_error}')
        return None, messages

    subject_group, group_error = context.resolve_subject_group(
        row.class_name,
        row.subject_name,
        row.subject_group_name or None,
    )
    if group_error:
        messages.append(f'ERROR: {group_error}')
        return None, messages

    existing = TeachingAssignment.objects.filter(
        class_subject=class_subject,
        term_id=context.term_id,
        stream=stream,
        subject_group=subject_group,
    ).first()
    if existing:
        messages.append(
            f'WARN: Will replace existing teaching assignment for '
            f'{class_level.name} {row.subject_name}.',
        )
        return 'replace', messages
    return 'create', messages


def _upsert_teacher(
    school,
    row: ParsedTeacherBulkRow,
    *,
    existing_phones: dict[str, User],
    teacher_cache: dict[str, User],
    summary: TeacherBulkImportSummary,
    messages: list[str],
) -> User:
    _resolve_teacher_action(row, school, existing_phones, messages)
    if messages:
        raise ValidationError({'detail': messages[-1].replace('ERROR: ', '')})

    phone = format_phone_number(row.phone_number)
    if phone in teacher_cache:
        return teacher_cache[phone]

    user = User.objects.filter(phone_number=phone).first()
    if user:
        user.first_name = row.first_name
        user.last_name = row.last_name
        user.email = row.email or ''
        user.is_active = True
        user.save(update_fields=['first_name', 'last_name', 'email', 'is_active', 'updated_at'])
        summary.teachers_updated += 1
    else:
        user = User.objects.create(
            school=school,
            first_name=row.first_name,
            last_name=row.last_name,
            phone_number=phone,
            role=User.RoleChoices.TEACHER,
            email=row.email or '',
            is_active=True,
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])
        Profile.objects.get_or_create(user=user)
        summary.teachers_created += 1
        existing_phones[phone] = user

    teacher_cache[phone] = user
    return user


def _apply_assignment(
    context,
    teacher: User,
    row: ParsedTeacherBulkRow,
    *,
    messages: list[str],
) -> tuple[bool, bool]:
    if not row.assignment_type:
        return False, False

    _, assignment_messages = _resolve_assignment_action(context, row)
    error_messages = [message for message in assignment_messages if message.startswith('ERROR:')]
    if error_messages:
        messages.extend(message.replace('ERROR: ', '') for message in error_messages)
        raise ValidationError({'detail': messages[-1]})

    class_level, _ = context.resolve_class_level(row.class_name)
    stream, _ = context.resolve_stream(class_level, row.stream_name or None)

    if row.assignment_type == ASSIGNMENT_TYPE_CLASS_TEACHER:
        existing = ClassTeacher.objects.filter(
            class_level=class_level,
            term_id=context.term_id,
            stream=stream,
        ).first()
        if existing:
            existing.delete()
        ClassTeacher.objects.create(
            teacher=teacher,
            class_level=class_level,
            stream=stream,
            term_id=context.term_id,
        )
        return existing is None, existing is not None

    class_subject, _ = context.resolve_class_subject(row.class_name, row.subject_name)
    subject_group, _ = context.resolve_subject_group(
        row.class_name,
        row.subject_name,
        row.subject_group_name or None,
    )
    existing = TeachingAssignment.objects.filter(
        class_subject=class_subject,
        term_id=context.term_id,
        stream=stream,
        subject_group=subject_group,
    ).first()
    if existing:
        existing.delete()
    TeachingAssignment.objects.create(
        teacher=teacher,
        class_subject=class_subject,
        stream=stream,
        subject_group=subject_group,
        term_id=context.term_id,
    )
    return existing is None, existing is not None


def _write_failure_export(
    school,
    failed_rows: list[dict],
    *,
    upload_format: str,
) -> TeacherBulkFailureExport:
    headers = [*IMPORT_HEADERS, *FAILURE_EXTRA_HEADERS]
    token = str(uuid.uuid4())
    expires_at = timezone.now() + settings.TEACHER_BULK_IMPORT_FAILURE_TTL
    path = get_failure_export_path(school.id, token, upload_format)
    path.parent.mkdir(parents=True, exist_ok=True)

    if upload_format == 'xlsx':
        payload = build_teacher_failure_xlsx(school, failed_rows)
    else:
        payload = build_csv_bytes(headers=headers, rows=failed_rows)

    path.write_bytes(payload)
    return TeacherBulkFailureExport(
        token=token,
        download_url=f'/api/v1/schools/setup/teachers/bulk-upload/failures/{token}/',
        expires_at=expires_at,
        format=upload_format,
    )


def _is_failure_export_expired(path: Path) -> bool:
    modified_at = timezone.datetime.fromtimestamp(
        path.stat().st_mtime,
        tz=datetime_timezone.utc,
    )
    return timezone.now() - modified_at > settings.TEACHER_BULK_IMPORT_FAILURE_TTL
