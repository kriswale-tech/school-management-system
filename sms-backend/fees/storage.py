import re

from django.core.files.storage import storages


def receipt_storage():
    return storages['receipts']


def _path_segment(value: str, *, fallback: str = 'unknown') -> str:
    cleaned = (value or '').strip()
    cleaned = cleaned.replace('/', '-').replace('\\', '-')
    cleaned = re.sub(r'[^\w\s.\-]', '', cleaned, flags=re.UNICODE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' .-_')
    return cleaned or fallback


def receipt_upload_to(instance, _filename):
    payment = instance.payment
    school_name = _path_segment(payment.student.school.name, fallback='school')
    academic_year = (payment.term.academic_year.academic_year or '').replace('/', '-')
    term_label = payment.term.get_term_display()
    year_term = _path_segment(f'{academic_year} {term_label}', fallback='term')
    number = _path_segment(instance.receipt_number, fallback='receipt').replace(' ', '_')
    if not number.lower().endswith('.pdf'):
        number = f'{number}.pdf'
    return f'{school_name}/fees/receipts/{year_term}/{number}'


def fee_schedule_upload_to(instance, _filename):
    school_name = _path_segment(instance.student.school.name, fallback='school')
    academic_year = (instance.term.academic_year.academic_year or '').replace('/', '-')
    term_label = instance.term.get_term_display()
    year_term = _path_segment(f'{academic_year} {term_label}', fallback='term')
    student_code = _path_segment(instance.student.student_id, fallback='student').replace(' ', '_')
    return f'{school_name}/fees/next-billings/{year_term}/{student_code}.pdf'
