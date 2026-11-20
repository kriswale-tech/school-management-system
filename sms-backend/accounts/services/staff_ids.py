"""School staff identification numbers.

Uses the school's student ID prefix so both sequences share one setting,
with an S marker so staff numbers stay distinct from student numbers.
"""

import re

from django.db import transaction
from rest_framework.exceptions import ValidationError

from accounts.models import SchoolMembership


def school_initials(name: str) -> str:
    words = re.findall(r'[A-Za-z0-9]+', name or '')
    if not words:
        return 'SCH'
    initials = ''.join(word[0].upper() for word in words)
    return initials[:6] or 'SCH'


def staff_id_prefix_for(school) -> str:
    prefix = (getattr(school, 'student_id_prefix', '') or '').strip().upper()
    if prefix:
        return prefix
    return school_initials(getattr(school, 'name', ''))


def normalize_staff_id(value: str | None) -> str:
    return (value or '').strip()


def generate_staff_id(*, school) -> str:
    """Next ID for this school, such as UA-S0001."""
    prefix = staff_id_prefix_for(school)
    pattern = f'{prefix}-S'
    with transaction.atomic():
        existing = (
            SchoolMembership.objects.select_for_update()
            .filter(school=school, staff_id__startswith=pattern)
            .values_list('staff_id', flat=True)
        )
        max_n = 0
        for staff_id in existing:
            suffix = staff_id[len(pattern):]
            if suffix.isdigit():
                max_n = max(max_n, int(suffix))
    return f'{pattern}{max_n + 1:04d}'


def assert_staff_id_available(*, school, staff_id: str, exclude_membership_id=None) -> None:
    queryset = SchoolMembership.objects.filter(school=school, staff_id=staff_id)
    if exclude_membership_id is not None:
        queryset = queryset.exclude(id=exclude_membership_id)
    if queryset.exists():
        raise ValidationError({
            'staff_id': 'A staff member with this ID already exists for this school.',
        })
