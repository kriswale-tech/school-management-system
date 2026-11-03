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
