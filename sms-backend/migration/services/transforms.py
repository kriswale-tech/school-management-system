import re
from datetime import date, datetime

from shared.helpers import format_phone_number

DATE_FORMATS = {
    '%Y-%m-%d': '2020-01-31',
    '%d/%m/%Y': '31/01/2020',
    '%m/%d/%Y': '01/31/2020',
    '%d-%m-%Y': '31-01-2020',
    '%d.%m.%Y': '31.01.2020',
}


MONTHS = {
    'jan': 1, 'january': 1,
    'feb': 2, 'february': 2,
    'mar': 3, 'march': 3,
    'apr': 4, 'april': 4,
    'may': 5,
    'jun': 6, 'june': 6,
    'jul': 7, 'july': 7,
    'aug': 8, 'august': 8,
    'sep': 9, 'sept': 9, 'september': 9,
    'oct': 10, 'october': 10,
    'nov': 11, 'november': 11,
    'dec': 12, 'december': 12,
}
_ORDINAL = re.compile(r'(\d+)(st|nd|rd|th)\b', re.IGNORECASE)


class TransformError(Exception):
    def __init__(self, message, *, blocked=True):
        super().__init__(message)
        self.blocked = blocked


def trim_value(value, _config):
    return value.strip() if isinstance(value, str) else value


def split_full_name(value, _config):
    parts = [part for part in str(value or '').split() if part]
    if not parts:
        return {'first_name': '', 'other_names': '', 'last_name': ''}
    if len(parts) == 1:
        return {'first_name': parts[0], 'other_names': '', 'last_name': ''}
    return {
        'first_name': parts[0],
        'other_names': ' '.join(parts[1:-1]),
        'last_name': parts[-1],
    }


def combine_values(raw_values, config):
    columns = config.get('columns') or []
    separator = config.get('separator', ' ')
    pieces = [str(raw_values.get(column, '') or '').strip() for column in columns]
    return separator.join(piece for piece in pieces if piece)


def _number(token, low, high):
    if not token.isdigit():
        return None
    number = int(token)
    if low <= number <= high:
        return number
    return None


def _named_month_date(text):
    cleaned = _ORDINAL.sub(r'\1', text)
    cleaned = re.sub(r'\bof\b', ' ', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace(',', ' ')
    parts = [part for part in cleaned.split() if part]
    if len(parts) != 3:
        return ''
    day_first = (
        _number(parts[0], 1, 31),
        MONTHS.get(parts[1].lower()),
        _number(parts[2], 1000, 9999),
    )
    month_first = (
        _number(parts[1], 1, 31),
        MONTHS.get(parts[0].lower()),
        _number(parts[2], 1000, 9999),
    )
    for day, month, year in (day_first, month_first):
        if not (day and month and year):
            continue
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return ''
    return ''


def parse_date(value, config):
    text = str(value or '').strip()
    if not text:
        return ''
    named = _named_month_date(text)
    if named:
        return named
    if len(text) >= 10 and text[4:5] == '-' and text[7:8] == '-':
        candidate = text[:10]
        try:
            datetime.strptime(candidate, '%Y-%m-%d')
        except ValueError:
            pass
        else:
            return candidate
    selected = config.get('format') or ''
    if not selected:
        raise TransformError(
            'Choose a date format before this value can be read. Ambiguous dates are not guessed.',
        )
    if selected not in DATE_FORMATS:
        raise TransformError('That date format is not supported.')
    try:
        return datetime.strptime(text, selected).date().isoformat()
    except ValueError as exc:
        raise TransformError(f'"{text}" does not match the selected date format.') from exc


def normalize_phone(value, _config):
    text = str(value or '').strip()
    if not text:
        return ''
    try:
        return format_phone_number(text)
    except ValueError as exc:
        raise TransformError(str(exc), blocked=False) from exc


def map_value(value, config):
    mapping = config.get('map') or {}
    text = str(value or '').strip()
    if text in mapping:
        return mapping[text]
    lowered = {str(key).strip().lower(): mapped for key, mapped in mapping.items()}
    if text.lower() in lowered:
        return lowered[text.lower()]
    if config.get('keep_unknown', True):
        return text
    raise TransformError(f'"{text}" is not in the value map.')


STEPS = {
    'trim': trim_value,
    'split_name': split_full_name,
    'combine': combine_values,
    'date': parse_date,
    'phone': normalize_phone,
    'value_map': map_value,
}
