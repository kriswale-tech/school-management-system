import re

_INTERNATIONAL_PATTERN = re.compile(r'^\+233\d{9}$')
_LOCAL_PATTERN = re.compile(r'^0\d{9}$')


def format_phone_number(phone_number: str) -> str:
    phone_number = phone_number.strip()

    if _INTERNATIONAL_PATTERN.match(phone_number):
        return phone_number

    if _LOCAL_PATTERN.match(phone_number):
        return f'+233{phone_number[1:]}'

    raise ValueError(
        'Invalid phone number format. Expected +233XXXXXXXXX or 0XXXXXXXXX.'
    )
