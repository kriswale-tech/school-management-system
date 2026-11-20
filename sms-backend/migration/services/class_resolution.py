"""Resolve source class text against the school's existing classes and streams."""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from academics.models import ClassStream
from migration.models import ClassValueResolution, MigrationJob, MigrationRow


def _text(value):
    return str(value or '').strip()


def _key(value):
    return ' '.join(_text(value).casefold().split())


def is_operational(stream):
    level = stream.class_level.level
    class_level = stream.class_level
    return (
        stream.is_active
        and not stream.is_migration_snapshot
        and class_level.is_active
        and not class_level.is_migration_snapshot
        and level.is_active
        and not level.is_migration_snapshot
    )


def load_streams(school_id):
    return list(
        ClassStream.objects.filter(class_level__school_id=school_id).select_related(
            'class_level',
            'class_level__level',
        )
    )


def saved_map(job):
    return {
        item.source_value: item
        for item in ClassValueResolution.objects.filter(job=job).select_related('stream__class_level')
    }


def _pack(stream, *, source_value, label, status, message, use_snapshot=False):
    return {
        'source_value': source_value,
        'label': label,
        'status': status,
        'stream_id': str(stream.id) if stream is not None else '',
        'class_label': stream.class_level.name if stream is not None else '',
        'stream_label': '' if stream is None or stream.is_default else stream.name,
        'message': message,
        'use_snapshot': use_snapshot,
    }


def resolve_placement(streams, class_name, stream_name, *, current, memory=None):
    allowed = [stream for stream in streams if is_operational(stream)] if current else list(streams)
    raw_class = _text(class_name)
    raw_stream = _text(stream_name)
    label = raw_class if not raw_stream else f'{raw_class} {raw_stream}'
    source_value = _key(label)
    if not source_value:
        return _pack(None, source_value='', label='', status='none', message='')

    exact = [stream for stream in allowed if _key(stream.full_name) == source_value]
    if len(exact) == 1:
        stream = exact[0]
        named = [
            item for item in allowed
            if item.class_level_id == stream.class_level_id and not item.is_default
        ]
        class_only = not raw_stream and _key(stream.class_level.name) == source_value
        if named and class_only and stream.is_default:
            return _pack(
                None,
                source_value=source_value,
                label=label,
                status='unresolved',
                message=f'{stream.class_level.name} has streams. Choose one before saving.',
            )
        return _pack(stream, source_value=source_value, label=label, status='exact', message='Matches an existing class.')
    if len(exact) > 1:
        return _pack(
            None,
            source_value=source_value,
            label=label,
            status='unresolved',
            message='More than one class matches this name. Choose one.',
        )

    if raw_class:
        combo = []
        for stream in allowed:
            stream_label = '' if stream.is_default else stream.name
            if _key(stream.class_level.name) == _key(raw_class) and _key(stream_label) == _key(raw_stream):
                combo.append(stream)
        if len(combo) == 1:
            return _pack(
                combo[0],
                source_value=source_value,
                label=label,
                status='exact',
                message='Matches this class and stream.',
            )
        if len(combo) > 1:
            return _pack(
                None,
                source_value=source_value,
                label=label,
                status='unresolved',
                message='More than one stream matches. Choose one.',
            )

    remembered = _remembered_placement(memory, source_value, label, current)
    if remembered is not None:
        return remembered

    class_matches = [stream for stream in allowed if _key(stream.class_level.name) == _key(raw_class or label)]
    named = [stream for stream in class_matches if not stream.is_default]
    if class_matches and not raw_stream and not named and len(class_matches) == 1:
        return _pack(
            class_matches[0],
            source_value=source_value,
            label=label,
            status='exact',
            message='Matches an existing class.',
        )
    if named and not raw_stream and _key(raw_class or label) == _key(named[0].class_level.name):
        return _pack(
            None,
            source_value=source_value,
            label=label,
            status='unresolved',
            message=f'{named[0].class_level.name} has streams. Choose one before saving.',
        )

    suggestions = _suggest_split(allowed, source_value)
    if len(suggestions) == 1:
        stream = suggestions[0]
        stream_text = f', stream {stream.name}' if stream.name else ''
        return _pack(
            stream,
            source_value=source_value,
            label=label,
            status='inferred',
            message=f'Suggested {stream.class_level.name}{stream_text}. Confirm this before saving.',
        )
    if len(suggestions) > 1:
        return _pack(
            None,
            source_value=source_value,
            label=label,
            status='unresolved',
            message='This could be more than one class. Choose the right one.',
        )
    similar = _similar_stream(allowed, source_value)
    if similar is not None:
        return _pack(
            similar,
            source_value=source_value,
            label=label,
            status='inferred',
            message=f'"{label}" looks like {similar.full_name}. Confirm this before saving.',
        )
    if current:
        return _pack(
            None,
            source_value=source_value,
            label=label,
            status='unresolved',
            message=f'"{label}" is not a current class. Add it in Classes, then choose it here.',
        )
    return _pack(
        None,
        source_value=source_value,
        label=label,
        status='snapshot',
        message='This past class will be kept as an inactive historical class.',
        use_snapshot=True,
    )


def load_class_memory(school):
    from migration.models import SchoolValueMapping

    return {
        item.source_value: item
        for item in SchoolValueMapping.objects.filter(
            school=school,
            field_name='class_name',
        ).select_related('stream__class_level__level')
    }


def _remembered_placement(memory, source_value, label, current):
    remembered = (memory or {}).get(source_value)
    if remembered is None:
        return None
    if remembered.stream_id and (not current or is_operational(remembered.stream)):
        return _pack(
            remembered.stream,
            source_value=source_value,
            label=label,
            status='approved',
            message='Used a class this school already approved.',
        )
    if remembered.canonical_value == 'snapshot' and not current:
        return _pack(
            None,
            source_value=source_value,
            label=label,
            status='approved',
            message='This school already chose to keep this as an old class.',
            use_snapshot=True,
        )
    return None


def _similar_stream(streams, source_value):
    from difflib import get_close_matches

    names = {_key(stream.full_name): stream for stream in streams}
    match = get_close_matches(source_value, list(names), n=1, cutoff=0.86)
    if not match:
        return None
    return names[match[0]]


def _suggest_split(streams, source_value):
    by_class = {}
    for stream in streams:
        by_class.setdefault(stream.class_level_id, stream.class_level.name)
    for class_id, class_label in sorted(by_class.items(), key=lambda item: len(_key(item[1])), reverse=True):
        prefix = _key(class_label)
        if not prefix or not source_value.startswith(prefix):
            continue
        remainder = source_value[len(prefix):].strip()
        if not remainder:
            continue
        compact = remainder.replace(' ', '')
        matches = []
        for stream in streams:
            if stream.class_level_id != class_id or stream.is_default:
                continue
            stream_key = _key(stream.name)
            if stream_key == remainder or stream_key.replace(' ', '') == compact:
                matches.append(stream)
        if matches:
            return matches
    return []


def apply_saved(resolved, saved, *, current):
    choice = saved.get(resolved.get('source_value') or '')
    if choice is None or resolved.get('status') == 'none':
        return resolved
    if choice.use_snapshot:
        if current:
            return {
                **resolved,
                'status': 'unresolved',
                'stream_id': '',
                'use_snapshot': False,
                'message': 'A current class cannot be saved as an old class.',
            }
        return {
            **resolved,
            'status': 'confirmed',
            'stream_id': '',
            'class_label': '',
            'stream_label': '',
            'use_snapshot': True,
            'message': 'You chose to keep this as an old class.',
        }
    stream = choice.stream
    if stream is None:
        return resolved
    if current and not is_operational(stream):
        return {
            **resolved,
            'status': 'unresolved',
            'stream_id': '',
            'message': 'Choose a current class. Historical classes cannot be used this term.',
        }
    return {
        **resolved,
        'status': 'confirmed',
        'stream_id': str(stream.id),
        'class_label': stream.class_level.name,
        'stream_label': '' if stream.is_default else stream.name,
        'use_snapshot': False,
        'message': 'You confirmed this class.',
    }


def _stream_option(stream):
    return {'stream_id': str(stream.id), 'label': stream.full_name}


def class_groups(job):
    from schools.models import Term

    streams = load_streams(job.school_id)
    saved = saved_map(job)
    memory = load_class_memory(job.school)
    active_term = Term.objects.filter(school_id=job.school_id, is_active=True).select_related('academic_year').first()
    groups = {}
    rows = MigrationRow.objects.filter(job=job, sheet__included=True).order_by('source_row_number')
    for row in rows:
        values = row.transformed_values or {}
        class_name = _text(values.get('class_name'))
        stream_name = _text(values.get('stream_name'))
        if not class_name and not stream_name:
            continue
        current = _row_is_current(job, values, active_term)
        resolved = apply_saved(
            resolve_placement(streams, class_name, stream_name, current=current, memory=memory),
            saved,
            current=current,
        )
        bucket = groups.setdefault(resolved['source_value'], {
            'label': resolved['label'],
            'count': 0,
            'current': False,
            'resolved': resolved,
        })
        bucket['count'] += 1
        if current:
            bucket['current'] = True
            bucket['resolved'] = resolved
    operational = [_stream_option(stream) for stream in streams if is_operational(stream)]
    historical = [_stream_option(stream) for stream in streams]
    payload = []
    for source_value, bucket in groups.items():
        resolved = bucket['resolved']
        payload.append({
            'source_value': source_value,
            'label': bucket['label'],
            'count': bucket['count'],
            'status': resolved['status'],
            'message': resolved['message'],
            'class_label': resolved.get('class_label') or '',
            'stream_label': resolved.get('stream_label') or '',
            'stream_id': resolved.get('stream_id') or '',
            'needs_confirmation': resolved['status'] in {'inferred', 'unresolved'},
            'automatic': resolved['status'] in {'exact', 'approved'},
            'options': operational if bucket['current'] else historical,
        })
    return payload


def _row_is_current(job, values, active_term):
    if job.template == MigrationJob.Template.STUDENT_INFORMATION:
        return True
    if active_term is None:
        return False
    from migration.services.student_plan import _normalize_term

    year_label = _text(values.get('academic_year'))
    term_key = _normalize_term(values.get('term'))
    return (
        active_term.academic_year.academic_year == year_label
        and active_term.term == term_key
    )


@transaction.atomic
def confirm_class_value(*, job, actor, source_value, stream_id='', use_snapshot=False):
    key = _key(source_value)
    if not key:
        raise ValidationError({'source_value': 'Choose a class value from the file.'})
    if job.template == MigrationJob.Template.STUDENT_INFORMATION and use_snapshot:
        raise ValidationError({'use_snapshot': 'Current classes must already exist.'})
    stream = None
    if stream_id:
        stream = ClassStream.objects.select_related('class_level__level').filter(
            id=stream_id,
            class_level__school=job.school,
        ).first()
        if stream is None:
            raise ValidationError({'stream_id': 'Choose a class in this school.'})
        if job.template == MigrationJob.Template.STUDENT_INFORMATION and not is_operational(stream):
            raise ValidationError({'stream_id': 'Choose a current class.'})
    elif not use_snapshot:
        raise ValidationError({'stream_id': 'Choose a class.'})
    ClassValueResolution.objects.update_or_create(
        job=job,
        source_value=key,
        defaults={
            'stream': stream,
            'use_snapshot': bool(use_snapshot and stream is None),
            'confirmed_by': actor,
        },
    )
    from django.utils import timezone

    from migration.models import SchoolValueMapping
    from migration.services.audit import record_migration_audit

    SchoolValueMapping.objects.update_or_create(
        school=job.school,
        field_name='class_name',
        source_value=key,
        defaults={
            'source_label': _text(source_value),
            'canonical_value': 'snapshot' if use_snapshot and stream is None else str(stream.id),
            'stream': stream,
            'origin': 'manual',
            'approved_by': actor,
            'approved_at': timezone.now(),
        },
    )
    record_migration_audit(
        school=job.school,
        job=job,
        actor=actor,
        action='mapping',
        summary=f'Approved class "{_text(source_value)}".',
        payload={'source_value': key, 'stream_id': str(stream.id) if stream else '', 'use_snapshot': bool(use_snapshot and stream is None)},
    )
