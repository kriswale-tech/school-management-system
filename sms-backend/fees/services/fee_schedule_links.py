"""Public signed per-student fee schedule links for guardians."""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core import signing

from fees.models import StudentFee
from students.models import Student

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
            'amount': fee.amount,
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
        'total': total,
        'items': items,
    }
