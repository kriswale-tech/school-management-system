"""Distinct source values for fixed SCHOOLASST fields. No model calls."""

from difflib import get_close_matches

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from migration.models import MigrationJob, MigrationRow, SchoolValueMapping
from migration.services.audit import record_migration_audit
from schools.models import AcademicYear
from students.models import StudentParent


def _text(value):
    return str(value or '').strip()


def _key(value):
    return ' '.join(_text(value).casefold().split())


def _choice_map(options):
    exact = {}
    for value, label in options:
        exact[_key(value)] = value
        exact[_key(label)] = value
    return exact


GENDER_OPTIONS = (('male', 'Male'), ('female', 'Female'), ('other', 'Other'))
STATUS_OPTIONS = (('active', 'Active'), ('left', 'Left'), ('graduated', 'Graduated'))
BOOL_OPTIONS = (('yes', 'Yes'), ('no', 'No'))
RELATION_OPTIONS = tuple((choice.value, choice.label) for choice in StudentParent.RelationshipChoices)

ENUMS = {
    'gender': {
        'label': 'Gender',
        'options': GENDER_OPTIONS,
        'exact': _choice_map(GENDER_OPTIONS),
        'aliases': {
            'm': 'male',
            'boy': 'male',
            'man': 'male',
            'f': 'female',
            'girl': 'female',
            'woman': 'female',
        },
        'templates': {'student_information'},
        'optional': False,
        'block': 'Choose Male, Female, or Other for "{value}".',
    },
    'student_status': {
        'label': 'Status',
        'options': STATUS_OPTIONS,
        'exact': _choice_map(STATUS_OPTIONS),
        'aliases': {
            'continuing': 'active',
            'current': 'active',
            'inactive': 'left',
            'withdrawn': 'left',
            'graduate': 'graduated',
            'completed': 'graduated',
            'alumni': 'graduated',
        },
        'templates': {'student_information'},
        'optional': True,
        'block': 'Choose Active, Left, or Graduated for "{value}".',
    },
    'guardian_relationship': {
        'label': 'Relationship',
        'options': RELATION_OPTIONS,
        'exact': _choice_map(RELATION_OPTIONS),
        'aliases': {
            'mum': 'mother',
            'mom': 'mother',
            'dad': 'father',
            'auntie': 'aunt',
        },
        'templates': {'student_information'},
        'optional': True,
        'block': 'Choose a relationship for "{value}".',
    },
    'is_new_student': {
        'label': 'New student',
        'options': BOOL_OPTIONS,
        'exact': {
            'yes': 'yes',
            'true': 'yes',
            'no': 'no',
            'false': 'no',
        },
        'aliases': {
            'y': 'yes',
            '1': 'yes',
            'n': 'no',
            '0': 'no',
        },
        'templates': {'student_information'},
        'optional': True,
        'block': 'Choose Yes or No for "{value}".',
    },
    'term': {
        'label': 'Term',
        'options': (
            ('first_term', 'First term'),
            ('second_term', 'Second term'),
            ('third_term', 'Third term'),
        ),
        'exact': {
            '1': 'first_term',
            'first': 'first_term',
            'first term': 'first_term',
            'first_term': 'first_term',
            'term 1': 'first_term',
            '2': 'second_term',
            'second': 'second_term',
            'second term': 'second_term',
            'second_term': 'second_term',
            'term 2': 'second_term',
            '3': 'third_term',
            'third': 'third_term',
            'third term': 'third_term',
            'third_term': 'third_term',
            'term 3': 'third_term',
        },
        'aliases': {
            'one': 'first_term',
            'two': 'second_term',
            'three': 'third_term',
        },
        'templates': {'opening_balances', 'historical_finance'},
        'optional': False,
        'block': 'Choose First term, Second term, or Third term for "{value}".',
    },
    'payment_method': {
        'label': 'Payment method',
        'options': (
            ('cash', 'Cash'),
            ('cheque', 'Cheque'),
            ('bank_transfer', 'Bank transfer'),
            ('mobile_money', 'Mobile money'),
            ('other', 'Other'),
        ),
        'exact': {
            'cash': 'cash',
            'cheque': 'cheque',
            'check': 'cheque',
            'bank transfer': 'bank_transfer',
            'bank': 'bank_transfer',
            'transfer': 'bank_transfer',
            'mobile money': 'mobile_money',
            'momo': 'mobile_money',
            'mobile_money': 'mobile_money',
            'other': 'other',
        },
        'aliases': {
            'mtn': 'mobile_money',
            'vodafone': 'mobile_money',
            'airteltigo': 'mobile_money',
        },
        'templates': {'historical_finance'},
        'optional': False,
        'block': 'Choose a payment method for "{value}".',
    },
    'payment_type': {
        'label': 'Payment type',
        'options': (
            ('ordinary', 'Ordinary'),
            ('advance', 'Advance'),
        ),
        'exact': {
            'ordinary': 'ordinary',
            'payment': 'ordinary',
            'normal': 'ordinary',
            'advance': 'advance',
            'credit': 'advance',
        },
        'aliases': {},
        'templates': {'historical_finance'},
        'optional': False,
        'block': 'Choose Ordinary or Advance for "{value}".',
    },
    'currency': {
        'label': 'Currency',
        'options': (
            ('ghs', 'GHS'),
        ),
        'exact': {
            'ghs': 'ghs',
            'gh₵': 'ghs',
            '₵': 'ghs',
            'cedi': 'ghs',
            'cedis': 'ghs',
            'ghana cedi': 'ghs',
            'ghana cedis': 'ghs',
        },
        'aliases': {},
        'templates': {'opening_balances'},
        'optional': False,
        'block': 'This ledger uses GHS. "{value}" cannot be imported.',
    },
}

OMITTED = '__omit__'


def enum_memory(school):
    rows = SchoolValueMapping.objects.filter(
        school=school,
        field_name__in=ENUMS,
    )
    return {(item.field_name, item.source_value): item for item in rows}


def resolve_enum(spec, raw, saved=None):
    key = _key(raw)
    if saved is not None and saved.canonical_value == OMITTED:
        return 'omitted', '', 'omit'
    if saved is not None and saved.canonical_value:
        return 'approved', saved.canonical_value, 'memory'
    if key in spec['exact']:
        return 'exact', spec['exact'][key], 'exact'
    if key in spec['aliases']:
        return 'suggested', spec['aliases'][key], 'alias'
    pool = {**spec['aliases'], **{_key(label): value for value, label in spec['options']}}
    match = get_close_matches(key, list(pool), n=1, cutoff=0.84)
    if match:
        return 'suggested', pool[match[0]], 'similar'
    return 'unmapped', '', 'none'


def _mapped_fields(job):
    from migration.models import FieldMapping

    return set(
        FieldMapping.objects.filter(
            sheet__migration_file__job=job,
            ignored=False,
        ).exclude(target_field='').values_list('target_field', flat=True)
    )


def canonical_year(raw):
    text = ' '.join(_text(raw).replace('-', '/').split()).replace(' / ', '/')
    parts = [part.strip() for part in text.split('/')]
    if len(parts) == 2 and all(part.isdigit() and len(part) == 4 for part in parts):
        start_year, end_year = int(parts[0]), int(parts[1])
        if end_year >= start_year:
            return f'{start_year}/{end_year}'
    return _text(raw)


def _year_labels(school):
    return list(
        AcademicYear.objects.filter(school=school)
        .order_by('academic_year')
        .values_list('academic_year', flat=True)
    )


def _academic_year_group(job, rows):
    memory = {
        item.source_value: item
        for item in SchoolValueMapping.objects.filter(school=job.school, field_name='academic_year')
    }
    known = set(_year_labels(job.school))
    counts = {}
    labels = {}
    for row in rows:
        raw = _raw_field(row, 'academic_year')
        if not raw:
            continue
        key = _key(raw)
        counts[key] = counts.get(key, 0) + 1
        labels.setdefault(key, raw)
    values = []
    option_labels = set(known)
    for key, count in sorted(counts.items()):
        saved = memory.get(key)
        label = canonical_year(labels[key])
        parts = label.split('/')
        patterned = (
            len(parts) == 2
            and all(part.isdigit() and len(part) == 4 for part in parts)
            and int(parts[1]) >= int(parts[0])
        )
        if saved is not None and saved.canonical_value:
            status, canonical, origin = 'approved', saved.canonical_value, saved.origin
        elif label in known or patterned:
            status, canonical, origin = 'exact', label, 'exact'
        else:
            status, canonical, origin = 'unmapped', '', 'none'
        if canonical:
            option_labels.add(canonical)
        values.append({
            'source_value': key,
            'label': labels[key],
            'count': count,
            'status': status,
            'canonical_value': canonical,
            'origin': origin,
            'needs_confirmation': status in {'suggested', 'unmapped'},
        })
    return {
        'field': 'academic_year',
        'label': 'Academic year',
        'distinct': len(values),
        'total': sum(item['count'] for item in values),
        'options': [{'value': label, 'label': label} for label in sorted(option_labels)],
        'can_omit': False,
        'values': values,
    }


def _approve_academic_year(job, actor, item):
    source = _key(item.get('source_value') or item.get('label') or '')
    canonical = canonical_year(item.get('canonical_value'))
    known = set(_year_labels(job.school))
    patterned = canonical.count('/') == 1 and all(part.isdigit() and len(part) == 4 for part in canonical.split('/'))
    if not source or (canonical not in known and not patterned):
        raise ValidationError({'canonical_value': 'Choose a school year, or a year like 2020/2021.'})
    if patterned:
        start_year, end_year = (int(part) for part in canonical.split('/'))
        if end_year < start_year:
            raise ValidationError({'canonical_value': 'Choose a school year, or a year like 2020/2021.'})
    mapping, _created = SchoolValueMapping.objects.update_or_create(
        school=job.school,
        field_name='academic_year',
        source_value=source,
        defaults={
            'source_label': _text(item.get('label') or source),
            'canonical_value': canonical,
            'origin': 'manual',
            'approved_by': actor,
            'approved_at': timezone.now(),
        },
    )
    return mapping


def value_groups(job):
    if not job.template:
        return []
    mapped = _mapped_fields(job)
    memory = enum_memory(job.school)
    rows = list(MigrationRow.objects.filter(job=job, sheet__included=True).prefetch_related('sheet__field_mappings'))
    groups = []
    for field, spec in ENUMS.items():
        if job.template not in spec['templates'] or field not in mapped:
            continue
        counts = {}
        labels = {}
        for row in rows:
            raw = _raw_field(row, field)
            if not raw:
                continue
            key = _key(raw)
            counts[key] = counts.get(key, 0) + 1
            labels.setdefault(key, raw)
        values = []
        for key, count in sorted(counts.items(), key=lambda item: item[0]):
            saved = memory.get((field, key))
            status, canonical, origin = resolve_enum(spec, labels[key], saved)
            values.append({
                'source_value': key,
                'label': labels[key],
                'count': count,
                'status': status,
                'canonical_value': canonical,
                'origin': saved.origin if saved is not None else origin,
                'needs_confirmation': status in {'suggested', 'unmapped'},
            })
        groups.append({
            'field': field,
            'label': spec['label'],
            'distinct': len(values),
            'total': sum(item['count'] for item in values),
            'options': [{'value': value, 'label': label} for value, label in spec['options']],
            'can_omit': bool(spec.get('optional')),
            'values': values,
        })
    if job.template in {'opening_balances', 'historical_finance'} and 'academic_year' in mapped:
        groups.append(_academic_year_group(job, rows))
    return groups


def _raw_field(row, field):
    for mapping in row.sheet.field_mappings.all():
        if mapping.target_field == field and not mapping.ignored:
            raw = _text(row.raw_values.get(mapping.source_column))
            if raw:
                return raw
    return _text((row.transformed_values or {}).get(field))


def apply_row_enums(job, row, memory):
    values = dict(row.transformed_values or {})
    blocks = []
    if not job.template:
        return values, blocks
    for field, spec in ENUMS.items():
        if job.template not in spec['templates']:
            continue
        raw = _raw_field(row, field)
        if not raw:
            continue
        saved = memory.get((field, _key(raw)))
        status, canonical, _origin = resolve_enum(spec, raw, saved)
        if status == 'omitted':
            values.pop(field, None)
            continue
        if status in {'exact', 'approved'} and canonical:
            values[field] = canonical
        else:
            blocks.append({'column': field, 'message': spec['block'].format(value=raw)})
    return values, blocks


@transaction.atomic
def approve_values(*, job, actor, items):
    if not job.template:
        raise ValidationError({'template': 'Choose a template before approving values.'})
    saved = []
    for item in items:
        field = item.get('field') or ''
        if field == 'academic_year' and job.template in {'opening_balances', 'historical_finance'}:
            saved.append(_approve_academic_year(job, actor, item))
            continue
        spec = ENUMS.get(field)
        if spec is None or job.template not in spec['templates']:
            raise ValidationError({'field': f'{field} is not a value on this template.'})
        source = _key(item.get('source_value') or item.get('label') or '')
        canonical = _text(item.get('canonical_value'))
        allowed = {value for value, _label in spec['options']}
        if canonical == OMITTED:
            if not spec.get('optional'):
                raise ValidationError({'canonical_value': 'This value has to be matched.'})
        elif not source or canonical not in allowed:
            raise ValidationError({'canonical_value': 'Choose one of the listed values.'})
        if not source:
            raise ValidationError({'canonical_value': 'Choose one of the listed values.'})
        status, suggestion, origin = resolve_enum(spec, item.get('label') or source)
        if canonical == OMITTED:
            record_origin = 'omit'
        elif origin == 'exact' and canonical == suggestion:
            record_origin = 'exact'
        elif suggestion and canonical == suggestion:
            record_origin = 'suggestion'
        else:
            record_origin = 'manual'
        mapping, _created = SchoolValueMapping.objects.update_or_create(
            school=job.school,
            field_name=field,
            source_value=source,
            defaults={
                'source_label': _text(item.get('label') or source),
                'canonical_value': canonical,
                'origin': record_origin,
                'approved_by': actor,
                'approved_at': timezone.now(),
            },
        )
        saved.append(mapping)
    record_migration_audit(
        school=job.school,
        job=job,
        actor=actor,
        action='mapping',
        summary=f'Approved {len(saved)} source value{"s" if len(saved) != 1 else ""}.',
        payload={
            'values': [
                {
                    'field': item.field_name,
                    'source_value': item.source_value,
                    'canonical_value': item.canonical_value,
                    'origin': item.origin,
                }
                for item in saved
            ],
        },
    )
    return saved


def value_counts(job):
    return {
        group['field']: group['total']
        for group in value_groups(job)
    }
