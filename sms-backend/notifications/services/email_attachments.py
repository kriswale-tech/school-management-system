"""Read a stored PDF at send time so a guardian email can carry the file."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def load_email_attachment(spec: dict | None) -> tuple[str, bytes] | None:
    """Return ``(filename, pdf_bytes)`` for a queued attachment reference."""
    if not spec:
        return None
    kind = spec.get('kind')
    try:
        if kind == 'receipt':
            file_field = _receipt_field(spec.get('receipt_id'))
        elif kind == 'report':
            file_field = _report_field(spec.get('report_id'))
        elif kind == 'fee_schedule':
            file_field = _fee_schedule_field(spec.get('student_id'), spec.get('term_id'))
        else:
            return None
    except Exception:
        logger.exception('Could not look up %s PDF for email', kind)
        return None
    if file_field is None:
        return None
    return _read_file(file_field)


def _receipt_field(receipt_id):
    if not receipt_id:
        return None
    from fees.models import Receipt

    receipt = Receipt.objects.filter(id=receipt_id).first()
    if receipt is None:
        return None
    return receipt.file


def _report_field(report_id):
    if not report_id:
        return None
    from assessments.models import Report

    report = Report.objects.filter(id=report_id).first()
    if report is None:
        return None
    return report.file


def _fee_schedule_field(student_id, term_id):
    if not student_id or not term_id:
        return None
    from fees.models import FeeScheduleDocument

    document = FeeScheduleDocument.objects.filter(
        student_id=student_id,
        term_id=term_id,
    ).first()
    if document is None:
        return None
    return document.file


def _read_file(file_field) -> tuple[str, bytes] | None:
    name = getattr(file_field, 'name', '') or ''
    if not name:
        return None
    try:
        if not file_field.storage.exists(name):
            return None
        with file_field.open('rb') as handle:
            content = handle.read()
    except Exception:
        logger.exception('Could not read email attachment %s', name)
        return None
    if not content:
        return None
    filename = os.path.basename(str(name).replace('\\', '/')) or 'document.pdf'
    if not filename.lower().endswith('.pdf'):
        filename = f'{filename}.pdf'
    return filename, content
