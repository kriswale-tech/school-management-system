import io
from dataclasses import asdict

from django.conf import settings
from django.http import FileResponse
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from accounts.permissions import CanManageUser, HasActiveSchool
from schools.services.teachers_bulk_import import (
    commit_teacher_bulk_import,
    detect_upload_format,
    load_failure_export,
    parse_teacher_bulk_upload,
    preview_teacher_bulk_import,
)
from schools.services.teachers_bulk_template import build_teacher_import_template
from schools.setup_serializers.teachers_bulk_import import (
    TeacherBulkImportConfirmResponseSerializer,
    TeacherBulkImportPreviewResponseSerializer,
)
from shared.views import SchoolScopedAPIView


def _parse_dry_run(value: str | None) -> bool:
    if value is None:
        raise ValidationError({'dry_run': 'This query parameter is required.'})
    normalized = value.strip().lower()
    if normalized in {'1', 'true', 'yes'}:
        return True
    if normalized in {'0', 'false', 'no'}:
        return False
    raise ValidationError({'dry_run': 'Expected true or false.'})


def _validate_uploaded_file(uploaded_file):
    if uploaded_file is None:
        raise ValidationError({'file': 'An import file is required.'})

    if uploaded_file.size > settings.TEACHER_BULK_IMPORT_MAX_FILE_SIZE:
        max_bytes = settings.TEACHER_BULK_IMPORT_MAX_FILE_SIZE
        if max_bytes >= 1024 * 1024:
            size_label = f'{max_bytes // (1024 * 1024)} MB'
        else:
            size_label = f'{max_bytes // 1024} KB'
        raise ValidationError({'file': f'Import file must be {size_label} or smaller.'})

    return uploaded_file


def _serialize_preview_result(result):
    payload = {
        'dry_run': True,
        'summary': asdict(result.summary),
        'rows': [asdict(row) for row in result.rows],
    }
    return TeacherBulkImportPreviewResponseSerializer(payload).data


def _serialize_confirm_result(result):
    failures = None
    if result.failures is not None:
        failures = {
            'count': result.summary.rows_failed,
            'download_url': result.failures.download_url,
            'expires_at': result.failures.expires_at,
            'format': result.failures.format,
        }

    payload = {
        'dry_run': False,
        'summary': asdict(result.summary),
        'failures': failures,
    }
    return TeacherBulkImportConfirmResponseSerializer(payload).data


@extend_schema(
    summary='Download teacher bulk import template',
    description=(
        'Returns an Excel template for bulk teacher import. The workbook includes '
        'Import and Reference sheets plus dropdowns for class, subject, and '
        'assignment values configured for the current school.'
    ),
    responses={
        200: OpenApiResponse(description='Excel template file (.xlsx).'),
    },
)
class TeacherBulkImportTemplateView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, CanManageUser]

    def get(self, request):
        payload = build_teacher_import_template(self.school)
        return FileResponse(
            io.BytesIO(payload),
            as_attachment=True,
            filename='teacher-import-template.xlsx',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )


@extend_schema(
    summary='Upload teachers bulk import file',
    description=(
        'Uploads a teacher import file for preview or commit. Accepts .xlsx and .csv '
        'files up to the configured size limit. Use dry_run=true to validate without '
        'saving; dry_run=false commits valid rows and returns a temporary failure '
        'export when some rows fail.'
    ),
    parameters=[
        OpenApiParameter(
            name='dry_run',
            location=OpenApiParameter.QUERY,
            required=True,
            type=bool,
            description='Set to true to preview the import without saving.',
        ),
    ],
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'file': {'type': 'string', 'format': 'binary'},
            },
            'required': ['file'],
        },
    },
    responses={
        200: TeacherBulkImportPreviewResponseSerializer,
        201: TeacherBulkImportConfirmResponseSerializer,
    },
)
class TeacherBulkImportUploadView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, CanManageUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        dry_run = _parse_dry_run(request.query_params.get('dry_run'))
        uploaded_file = _validate_uploaded_file(request.FILES.get('file'))
        upload_format = detect_upload_format(uploaded_file.name, uploaded_file.content_type)
        file_bytes = uploaded_file.read()
        rows = parse_teacher_bulk_upload(file_bytes, upload_format=upload_format)

        if not rows:
            raise ValidationError({'file': 'No import rows were found in the uploaded file.'})

        if dry_run:
            result = preview_teacher_bulk_import(self.school, rows)
            return Response(_serialize_preview_result(result))

        result = commit_teacher_bulk_import(
            self.school,
            rows,
            upload_format=upload_format,
        )
        return Response(_serialize_confirm_result(result))


@extend_schema(
    summary='Download teacher bulk import failures',
    description=(
        'Downloads the temporary failure export generated after a bulk import '
        'confirm request. The file format matches the uploaded import format.'
    ),
    responses={
        200: OpenApiResponse(description='Failed import rows file (.xlsx or .csv).'),
        404: OpenApiResponse(description='Failure export not found or expired.'),
    },
)
class TeacherBulkImportFailuresDownloadView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, CanManageUser]

    def get(self, request, token):
        path, upload_format = load_failure_export(self.school.id, token)
        filename = f'teacher-import-failures.{upload_format}'
        content_type = (
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            if upload_format == 'xlsx'
            else 'text/csv'
        )
        return FileResponse(
            path.open('rb'),
            as_attachment=True,
            filename=filename,
            content_type=content_type,
        )
