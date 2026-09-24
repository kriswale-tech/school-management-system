"""Generate and store student report PDFs on R2."""

from __future__ import annotations

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework.exceptions import NotFound

from assessments.models import Report
from assessments.services.report import get_student_report_preview
from assessments.storage import student_report_filename
from schools.models import Term
from students.services import resolve_term


def _format_score(value) -> str:
    if value is None:
        return ''
    number = float(value)
    return str(int(number)) if number.is_integer() else f'{number:.2f}'


def _format_total_cell(value, max_value) -> str:
    score = _format_score(value)
    highest = _format_score(max_value)
    if not score and not highest:
        return ''
    if not score:
        return f'({highest})' if highest else ''
    if not highest:
        return score
    return f'{score} ({highest})'


def _chunk_bands(items: list, columns: int = 3) -> list[list]:
    if not items:
        return []
    size = max(1, (len(items) + columns - 1) // columns)
    chunks = [items[index:index + size] for index in range(0, len(items), size)]
    return [chunk for chunk in chunks if chunk]


def _pdf_context(payload: dict) -> dict:
    school = payload['school']
    contact_line = ' • '.join(
        part
        for part in [
            school.get('box_address') or '',
            school.get('address') or '',
            f"Tel: {school['phone_number']}" if school.get('phone_number') else '',
            f"Alt: {school['phone_number_alt']}" if school.get('phone_number_alt') else '',
        ]
        if part
    )
    subjects = []
    for row in payload['subjects']:
        subjects.append({
            **row,
            'class_score_display': _format_score(row.get('class_score')),
            'exam_score_display': _format_score(row.get('exam_score')),
            'total_display': _format_score(row.get('total')),
        })
    totals = payload['totals']
    return {
        **payload,
        'school': {
            **school,
            'name': (school.get('name') or '').upper(),
        },
        'contact_line': contact_line,
        'subjects': subjects,
        'totals': {
            **totals,
            'class_score_display': _format_total_cell(
                totals.get('class_score'),
                totals.get('max_class_score'),
            ),
            'exam_score_display': _format_total_cell(
                totals.get('exam_score'),
                totals.get('max_exam_score'),
            ),
            'total_display': _format_total_cell(
                totals.get('total'),
                totals.get('max_total'),
            ),
        },
        'grade_columns': _chunk_bands(payload.get('grade_bands') or []),
    }


def render_report_pdf(payload: dict) -> bytes:
    from weasyprint import HTML

    html = render_to_string('assessments/report_sheet.html', _pdf_context(payload))
    return HTML(string=html).write_pdf()


def _signed_url(report: Report) -> str | None:
    if not report.file:
        return None
    return report.file.url


def _report_file_exists(report: Report) -> bool:
    if not report.file or not report.file.name:
        return False
    try:
        return report.file.storage.exists(report.file.name)
    except Exception:
        return False


def serialize_stored_report(report: Report) -> dict:
    expire = getattr(settings, 'R2_SIGNED_URL_EXPIRE_SECONDS', 3600)
    return {
        'id': str(report.id),
        'student_id': str(report.student_id),
        'stream_id': str(report.stream_id),
        'term_id': str(report.term_id),
        'generated_at': report.generated_at.isoformat() if report.generated_at else None,
        'url': _signed_url(report),
        'url_expires_in': expire,
        'status': 'ready',
    }


def get_stored_student_report(*, school, stream_id, student_id, term_id=None) -> dict:
    term = resolve_term(school, term_id)
    report = (
        Report.objects.filter(
            school=school,
            stream_id=stream_id,
            student_id=student_id,
            term_id=term.id,
        )
        .select_related('term', 'term__academic_year')
        .first()
    )
    # Treat missing DB row, empty file field, or deleted R2 object the same:
    # frontend auto-generates on 404.
    if report is None or not _report_file_exists(report):
        raise NotFound('Report has not been generated yet.')
    return serialize_stored_report(report)

@transaction.atomic
def generate_student_report(
    *,
    school,
    membership,
    stream_id,
    student_id,
    term_id=None,
) -> dict:
    payload = get_student_report_preview(
        school=school,
        stream_id=stream_id,
        student_id=student_id,
        term_id=term_id,
    )
    term = Term.objects.select_related('academic_year').get(id=payload['term_id'])
    pdf_bytes = render_report_pdf(payload)

    report, _created = Report.objects.select_for_update().get_or_create(
        school=school,
        student_id=student_id,
        stream_id=stream_id,
        term_id=term.id,
    )
    report = (
        Report.objects.select_related(
            'school',
            'student',
            'stream',
            'stream__class_level',
            'term',
            'term__academic_year',
        ).get(pk=report.pk)
    )

    filename = student_report_filename(
        first_name=report.student.first_name,
        last_name=report.student.last_name,
    )
    if report.file:
        try:
            report.file.delete(save=False)
        except Exception:
            report.file.name = ''
    report.file.save(filename, ContentFile(pdf_bytes), save=False)
    report.generated_at = timezone.now()
    report.generated_by = getattr(membership, 'user', None)
    report.save()
    return serialize_stored_report(report)


def resolve_student_report_target(*, school, student_id, term_id=None):
    """Resolve stream + term from the student's enrollment."""
    from students.models import ClassEnrollment
    from students.services import get_student

    student = get_student(school=school, student_id=student_id)
    term = resolve_term(school, term_id)
    enrollment = (
        ClassEnrollment.objects.filter(student=student, term_id=term.id)
        .select_related('stream')
        .first()
    )
    if enrollment is None:
        raise NotFound('Student is not enrolled in this term.')
    return student, enrollment.stream, term


def get_student_profile_report(*, school, student_id, term_id=None) -> dict:
    student, stream, term = resolve_student_report_target(
        school=school,
        student_id=student_id,
        term_id=term_id,
    )
    return get_stored_student_report(
        school=school,
        stream_id=stream.id,
        student_id=student.id,
        term_id=term.id,
    )


def generate_student_profile_report(*, school, membership, student_id, term_id=None) -> dict:
    student, stream, term = resolve_student_report_target(
        school=school,
        student_id=student_id,
        term_id=term_id,
    )
    return generate_student_report(
        school=school,
        membership=membership,
        stream_id=stream.id,
        student_id=student.id,
        term_id=term.id,
    )
