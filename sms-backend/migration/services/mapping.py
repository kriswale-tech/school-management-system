from django.db import transaction
from rest_framework.exceptions import ValidationError

from migration.models import FieldMapping, MappingProfile, MigrationTransform
from migration.targets import DATE_FIELDS, PHONE_FIELDS, aliases_for, fields_for


def suggest_mappings(headers, job_type, template='', role=''):
    fields = fields_for(job_type, template, role)
    known = {key for key, _label, _required in fields}
    aliases = aliases_for(template, role)
    suggestions = []
    used = set()
    for header in headers:
        normalized = ' '.join(header.strip().lower().split())
        target = aliases.get(normalized, '')
        if target not in known or target in used:
            suggestions.append({
                'source_column': header,
                'target_field': '',
                'ignored': True,
                'suggested': False,
                'transforms': [],
            })
            continue
        used.add(target)
        suggestions.append({
            'source_column': header,
            'target_field': target,
            'ignored': False,
            'suggested': True,
            'transforms': _suggested_transforms(target, template),
        })
    return suggestions


def _suggested_transforms(target, template=''):
    if target == 'full_name':
        return [{'step': 'split_name', 'config': {}}]
    if target in DATE_FIELDS:
        return [{'step': 'date', 'config': {'format': '%d/%m/%Y'}}]
    if target in PHONE_FIELDS:
        return [{'step': 'phone', 'config': {}}]
    if target == 'gender' and not template:
        return [{
            'step': 'value_map',
            'config': {
                'map': {
                    'M': 'male',
                    'F': 'female',
                    'Male': 'male',
                    'Female': 'female',
                },
            },
        }]
    return [{'step': 'trim', 'config': {}}]


def unmapped_required(suggestions, job_type, template='', role=''):
    fields = fields_for(job_type, template, role)
    mapped = {
        item['target_field']
        for item in suggestions
        if item.get('target_field') and not item.get('ignored')
    }
    if 'full_name' in mapped:
        mapped.update({'first_name', 'last_name'})
    return [
        {'key': key, 'label': label}
        for key, label, required in fields
        if required and key not in mapped and key != 'full_name'
    ]


def _replace_mappings(owner_field, owner, mappings):
    existing = FieldMapping.objects.filter(**{owner_field: owner})
    MigrationTransform.objects.filter(field_mapping__in=existing).delete()
    existing.delete()
    created = []
    for position, item in enumerate(mappings):
        source = (item.get('source_column') or '').strip()
        if not source:
            raise ValidationError({'mappings': 'Each mapping needs a source column.'})
        mapping = FieldMapping.objects.create(
            **{owner_field: owner},
            source_column=source,
            target_field=(item.get('target_field') or '').strip(),
            ignored=bool(item.get('ignored')),
            position=position,
        )
        for step_index, step in enumerate(item.get('transforms') or []):
            name = step.get('step')
            if name not in MigrationTransform.Step.values:
                raise ValidationError({'transforms': f'Unknown transform "{name}".'})
            MigrationTransform.objects.create(
                field_mapping=mapping,
                step=name,
                config=step.get('config') or {},
                position=step_index,
            )
        created.append(mapping)
    return created


@transaction.atomic
def save_sheet_mapping(*, sheet, mappings):
    job = sheet.migration_file.job
    allowed = {
        key for key, _label, _required in fields_for(
            job.job_type,
            job.template,
            sheet.migration_file.role,
        )
    }
    for item in mappings:
        target = (item.get('target_field') or '').strip()
        if target and target not in allowed:
            raise ValidationError({'target_field': f'{target} is not a field on this template.'})
    return _replace_mappings('sheet', sheet, mappings)


@transaction.atomic
def save_profile(*, school, user, name, job_type, source_system, mappings):
    profile, _created = MappingProfile.objects.get_or_create(
        school=school,
        job_type=job_type,
        name=name.strip(),
        defaults={'source_system': source_system, 'created_by': user},
    )
    if profile.source_system != source_system:
        profile.source_system = source_system
        profile.save(update_fields=['source_system', 'updated_at'])
    _replace_mappings('profile', profile, mappings)
    return profile


def mapping_payload(mappings):
    payload = []
    for mapping in mappings:
        payload.append({
            'id': str(mapping.id),
            'source_column': mapping.source_column,
            'target_field': mapping.target_field,
            'ignored': mapping.ignored,
            'transforms': [
                {
                    'step': step.step,
                    'config': step.config,
                }
                for step in mapping.transforms.all()
            ],
        })
    return payload


def copy_profile_to_sheet(*, profile, sheet):
    mappings = mapping_payload(profile.field_mappings.prefetch_related('transforms'))
    save_sheet_mapping(sheet=sheet, mappings=mappings)
    sheet.mapping_profile = profile
    sheet.save(update_fields=['mapping_profile', 'updated_at'])
