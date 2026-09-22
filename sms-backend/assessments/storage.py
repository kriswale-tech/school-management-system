import re

from django.core.files.storage import storages


def report_storage():
    return storages['reports']


def _path_segment(value: str, *, fallback: str = 'unknown') -> str:
    """Keep readable names; strip path separators and unsafe characters."""
    cleaned = (value or '').strip()
    cleaned = cleaned.replace('/', '-').replace('\\', '-')
    cleaned = re.sub(r'[^\w\s.\-]', '', cleaned, flags=re.UNICODE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' .-_')
    return cleaned or fallback


def student_report_filename(*, first_name: str, last_name: str) -> str:
    first = _path_segment(first_name, fallback='student').replace(' ', '_')
    last = _path_segment(last_name, fallback='').replace(' ', '_')
    base = '_'.join(part for part in [first, last] if part) or 'student'
    return f'{base}.pdf'


def report_upload_to(instance, filename):
    school_name = _path_segment(instance.school.name, fallback='school')

    academic_year = (instance.term.academic_year.academic_year or '').replace('/', '-')
    term_label = instance.term.get_term_display()
    year_term = _path_segment(f'{academic_year} {term_label}', fallback='term')

    class_name = _path_segment(instance.stream.full_name, fallback='class')
    safe_name = filename if filename.lower().endswith('.pdf') else f'{filename}.pdf'
    safe_name = _path_segment(safe_name[:-4], fallback='student') + '.pdf'
    safe_name = safe_name.replace(' ', '_')

    return f'{school_name}/{year_term}/{class_name}/{safe_name}'
