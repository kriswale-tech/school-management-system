"""Public signed per-student fee schedule links for guardians."""

from __future__ import annotations

import hashlib
import json
import logging
from decimal import Decimal

from django.conf import settings
from django.core import signing
from django.core.files.base import ContentFile
from django.template.loader import render_to_string

from fees.models import FeeScheduleDocument, StudentFee
from students.models import Student

logger = logging.getLogger(__name__)

FEE_SCHEDULE_SALT = 'guardian-fee-schedule-v1'


def fee_schedule_link_max_age_seconds() -> int:
    return int(
        getattr(
            settings,
            'FEE_SCHEDULE_LINK_MAX_AGE_SECONDS',
            getattr(settings, 'RECEIPT_LINK_MAX_AGE_SECONDS', 60 * 60 * 24 * 30),
        ),
    )


def public_base_url() -> str:
    return getattr(settings, 'PUBLIC_BASE_URL', 'http://localhost:9000').rstrip('/')


def make_fee_schedule_token(*, student_id, term_id) -> str:
    return signing.dumps(
        {'sid': str(student_id), 'tid': str(term_id)},
        salt=FEE_SCHEDULE_SALT,
    )


def build_fee_schedule_public_url(*, student_id, term_id) -> str:
    token = make_fee_schedule_token(student_id=student_id, term_id=term_id)
    return f'{public_base_url()}/api/v1/public/fee-schedules/{token}/'


def load_fee_schedule_from_token(token: str) -> tuple[Student, object, list[StudentFee]]:
    """Return student, term, and StudentFee rows for a valid token."""
    try:
        payload = signing.loads(
            token,
            salt=FEE_SCHEDULE_SALT,
            max_age=fee_schedule_link_max_age_seconds(),
        )
    except signing.SignatureExpired as exc:
        raise ValueError('This fee schedule link has expired.') from exc
    except signing.BadSignature as exc:
        raise ValueError('This fee schedule link is invalid.') from exc

    student_id = payload.get('sid')
    term_id = payload.get('tid')
    if not student_id or not term_id:
        raise ValueError('This fee schedule link is invalid.')

    student = (
        Student.objects.select_related('school')
        .filter(id=student_id)
        .first()
    )
    if student is None:
        raise ValueError('Fee schedule not found.')

    from schools.models import Term

    term = (
        Term.objects.select_related('academic_year')
        .filter(id=term_id, school_id=student.school_id)
        .first()
    )
    if term is None:
        raise ValueError('Fee schedule not found.')

    fees = list(
        StudentFee.objects.filter(student=student, term=term)
        .select_related('fee_item')
        .order_by('name'),
    )
    if not fees:
        raise ValueError('Fee schedule not found.')
    return student, term, fees


def build_fee_schedule_context(*, student: Student, term, fees: list[StudentFee]) -> dict:
    school = student.school
    student_name = ' '.join(
        part
        for part in (student.first_name, student.other_names, student.last_name)
        if part
    ).strip()
    term_label = f'{term.academic_year.academic_year} · {term.get_term_display()}'
    total = sum((fee.amount for fee in fees), Decimal('0.00'))
    items = [
        {
            'name': fee.name,
            'amount': f'{fee.amount:.2f}',
            'description': (fee.fee_item.description if fee.fee_item_id else '') or '',
        }
        for fee in fees
    ]
    return {
        'school_name': school.name,
        'school_phone': school.phone_number,
        'school_email': school.email or '',
        'school_address': school.address or '',
        'student_name': student_name,
        'student_code': student.student_id,
        'term_label': term_label,
        'begins_on': term.start_date,
        'total': f'{total:.2f}',
        'items': items,
    }


def _schedule_fingerprint(context: dict) -> str:
    payload = {
        'school_name': context['school_name'],
        'school_phone': context['school_phone'] or '',
        'school_email': context['school_email'],
        'school_address': context['school_address'],
        'student_name': context['student_name'],
        'student_code': context['student_code'],
        'term_label': context['term_label'],
        'begins_on': context['begins_on'].isoformat(),
        'total': context['total'],
        'items': context['items'],
    }
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def _document_file_exists(document: FeeScheduleDocument) -> bool:
    name = getattr(document.file, 'name', '') or ''
    if not name:
        return False
    try:
        return document.file.storage.exists(name)
    except Exception:
        logger.exception('Could not check fee schedule for %s', document.student_id)
        return False


def fee_schedule_file_url(*, student, term) -> str | None:
    document = (
        FeeScheduleDocument.objects.filter(student=student, term=term)
        .first()
    )
    if document is None or not _document_file_exists(document):
        return None
    return document.file.url


def render_fee_schedule_pdf(*, student, term, fees) -> bytes:
    from weasyprint import HTML

    html = render_to_string(
        'fees/public/fee_schedule.html',
        build_fee_schedule_context(student=student, term=term, fees=fees),
    )
    return HTML(string=html).write_pdf()


def publish_fee_schedule_pdf(*, student, term) -> bool:
    """Store the current bill. Rewrite when the fees or the term date change."""
    fees = list(
        StudentFee.objects.filter(student=student, term=term)
        .select_related('fee_item')
        .order_by('name'),
    )
    if not fees:
        return False

    context = build_fee_schedule_context(student=student, term=term, fees=fees)
    digest = _schedule_fingerprint(context)
    document, _created = FeeScheduleDocument.objects.get_or_create(
        student=student,
        term=term,
    )
    if document.content_hash == digest and _document_file_exists(document):
        return True

    document = (
        FeeScheduleDocument.objects.select_related(
            'student__school',
            'term__academic_year',
        ).get(pk=document.pk)
    )
    try:
        pdf_bytes = render_fee_schedule_pdf(student=student, term=term, fees=fees)
        document.content_hash = digest
        document.file.save(
            f'{student.student_id}.pdf',
            ContentFile(pdf_bytes),
            save=False,
        )
        document.save(update_fields=['file', 'content_hash', 'updated_at'])
    except Exception:
        logger.exception(
            'Could not store fee schedule PDF for %s',
            student.student_id,
        )
        return False
    return _document_file_exists(document)
