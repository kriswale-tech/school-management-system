"""Public signed receipt links for guardian download (no login)."""

from __future__ import annotations

from django.conf import settings
from django.core import signing

from fees.models import Receipt

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

    receipt = (
        Receipt.objects.select_related(
            'payment',
            'payment__student',
            'payment__student__school',
            'payment__term',
            'payment__term__academic_year',
            'issued_by',
        )
        .filter(id=receipt_id)
        .first()
    )
    if receipt is None:
        raise ValueError('Receipt not found.')
    return receipt


def build_receipt_context(receipt: Receipt) -> dict:
    payment = receipt.payment
    student = payment.student
    school = student.school
    term = payment.term
    student_name = ' '.join(
        part
        for part in (student.first_name, student.other_names, student.last_name)
        if part
    ).strip()
    term_label = f'{term.academic_year.academic_year} · {term.get_term_display()}'
    return {
        'school_name': school.name,
        'school_phone': school.phone_number,
        'school_email': school.email or '',
        'school_address': school.address or '',
        'student_name': student_name,
        'student_id': student.student_id,
        'receipt_number': receipt.receipt_number,
        'amount': payment.amount,
        'payment_method': payment.get_payment_method_display(),
        'payment_reference': payment.payment_reference or '',
        'paid_at': payment.paid_at,
        'issued_at': receipt.issued_at,
        'term_label': term_label,
    }
