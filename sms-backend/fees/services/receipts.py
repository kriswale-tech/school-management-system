"""Public signed receipt links for guardian download (no login)."""

from __future__ import annotations

import logging

from django.conf import settings
from django.core import signing
from django.core.files.base import ContentFile
from django.template.loader import render_to_string

from fees.models import Receipt

logger = logging.getLogger(__name__)

RECEIPT_SALT = 'guardian-receipt-v1'


def receipt_link_max_age_seconds() -> int:
    return int(getattr(settings, 'RECEIPT_LINK_MAX_AGE_SECONDS', 60 * 60 * 24 * 30))


def public_base_url() -> str:
    return getattr(settings, 'PUBLIC_BASE_URL', 'http://localhost:9000').rstrip('/')


def make_receipt_token(receipt_id) -> str:
    return signing.dumps({'rid': str(receipt_id)}, salt=RECEIPT_SALT)


def build_receipt_public_url(receipt_id) -> str:
    token = make_receipt_token(receipt_id)
    return f'{public_base_url()}/api/v1/public/receipts/{token}/'


def _receipt_queryset():
    return Receipt.objects.select_related(
        'payment',
        'payment__student',
        'payment__student__school',
        'payment__term',
        'payment__term__academic_year',
        'payment__recorded_by',
        'issued_by',
    ).prefetch_related('payment__allocations__term__academic_year')


def load_receipt_for_school(*, school, receipt_id) -> Receipt | None:
    return (
        _receipt_queryset()
        .filter(id=receipt_id, payment__student__school=school)
        .first()
    )


def load_receipt_from_token(token: str) -> Receipt:
    try:
        payload = signing.loads(
            token,
            salt=RECEIPT_SALT,
            max_age=receipt_link_max_age_seconds(),
        )
    except signing.SignatureExpired as exc:
        raise ValueError('This receipt link has expired.') from exc
    except signing.BadSignature as exc:
        raise ValueError('This receipt link is invalid.') from exc

    receipt_id = payload.get('rid')
    if not receipt_id:
        raise ValueError('This receipt link is invalid.')

    receipt = _receipt_queryset().filter(id=receipt_id).first()
    if receipt is None:
        raise ValueError('Receipt not found.')
    return receipt


def _user_display_name(user) -> str:
    if user is None:
        return ''
    return (user.get_full_name() or '').strip() or getattr(user, 'phone_number', '') or ''


def build_receipt_context(receipt: Receipt) -> dict:
    payment = receipt.payment
    student = payment.student
    school = student.school
    student_name = ' '.join(
        part
        for part in (student.first_name, student.other_names, student.last_name)
        if part
    ).strip()
    allocations = sorted(
        payment.allocations.all(),
        key=lambda row: (row.term.start_date, row.created_at),
    )
    allocation_rows = [
        {
            'term_label': (
                f'{row.term.academic_year.academic_year} · {row.term.get_term_display()}'
            ),
            'amount': f'{row.amount:.2f}',
        }
        for row in allocations
    ]
    if len(allocation_rows) == 1:
        term_label = allocation_rows[0]['term_label']
    elif allocation_rows:
        term_label = 'Multiple terms'
    else:
        term = payment.term
        term_label = f'{term.academic_year.academic_year} · {term.get_term_display()}'

    received_by = _user_display_name(payment.recorded_by) or _user_display_name(
        receipt.issued_by,
    )
    try:
        school_logo_url = school.logo.url if school.logo else None
    except (ValueError, AttributeError):
        school_logo_url = None
    return {
        'id': receipt.id,
        'school_name': school.name,
        'school_logo_url': school_logo_url,
        'school_phone': school.phone_number,
        'school_email': school.email or '',
        'school_address': school.address or '',
        'student_name': student_name,
        'student_id': student.student_id,
        'receipt_number': receipt.receipt_number,
        'amount': f'{payment.amount:.2f}',
        'payment_method': payment.get_payment_method_display(),
        'payment_reference': payment.payment_reference or '',
        'paid_at': payment.paid_at,
        'issued_at': receipt.issued_at,
        'received_by': received_by,
        'term_label': term_label,
        'allocations': allocation_rows,
    }


def _receipt_file_exists(receipt: Receipt) -> bool:
    name = getattr(receipt.file, 'name', '') or ''
    if not name:
        return False
    try:
        return receipt.file.storage.exists(name)
    except Exception:
        logger.exception('Could not check receipt file %s', receipt.receipt_number)
        return False


def receipt_file_url(receipt: Receipt) -> str | None:
    if not _receipt_file_exists(receipt):
        return None
    return receipt.file.url


def render_receipt_pdf(receipt: Receipt) -> bytes:
    from weasyprint import HTML

    html = render_to_string('fees/public/receipt.html', build_receipt_context(receipt))
    return HTML(string=html).write_pdf()


def _write_receipt_pdf(receipt: Receipt) -> None:
    pdf_bytes = render_receipt_pdf(receipt)
    receipt.file.save(
        f'{receipt.receipt_number}.pdf',
        ContentFile(pdf_bytes),
        save=True,
    )


def _schedule_receipt_notice(receipt: Receipt) -> None:
    from notifications.services.guardians import schedule_payment_receipt_notice

    payment = receipt.payment
    schedule_payment_receipt_notice(
        student_id=payment.student_id,
        payment_id=payment.id,
        receipt_id=receipt.id,
        receipt_number=receipt.receipt_number,
        amount=payment.amount,
    )


def publish_receipt_pdf(receipt: Receipt) -> None:
    """Store the PDF once. Tell guardians only after that first successful write."""
    already_stored = _receipt_file_exists(receipt)
    if not already_stored:
        try:
            _write_receipt_pdf(receipt)
        except Exception:
            logger.exception('Could not store receipt PDF %s', receipt.receipt_number)
            return
    if not already_stored and _receipt_file_exists(receipt):
        _schedule_receipt_notice(receipt)
