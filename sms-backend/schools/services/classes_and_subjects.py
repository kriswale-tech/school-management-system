from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import NotFound, ValidationError

from academics.models import ClassLevel, ClassSubject, ClassStream, Level, Subject, SubjectGroup
from academics.services import custom_curriculum as curriculum_ops
from schools.models import SchoolSetup
from schools.services.setup import advance_setup_if_needed, require_prior_setup_steps


def _raise_drf(exc: DjangoValidationError):
    if hasattr(exc, 'message_dict'):
        raise ValidationError(exc.message_dict) from exc
    if hasattr(exc, 'messages'):
        raise ValidationError(list(exc.messages)) from exc
    raise ValidationError(str(exc)) from exc


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except DjangoValidationError as exc:
        _raise_drf(exc)


def _serialize_stream(stream):
    return {
        'id': stream.id,
        'name': stream.name,
        'full_name': stream.full_name,
        'description': stream.description,
        'is_default': stream.is_default,
        'is_active': stream.is_active,
    }


def _serialize_subject_groups(class_subject):
    return [
        {
            'id': group.id,
            'name': group.name,
            'is_active': group.is_active,
        }
        for group in sorted(class_subject.groups.all(), key=lambda item: item.name)
    ]


def _serialize_class_subject(class_subject):
    return {
        'id': class_subject.subject.id,
        'class_subject_id': class_subject.id,
        'name': class_subject.subject.name,
        'is_active': class_subject.subject.is_active,
        'is_system_generated': class_subject.is_system_generated,
        'is_editable': not class_subject.is_system_generated,
        'groups': _serialize_subject_groups(class_subject),
    }


def _serialize_class_level(class_level):
    # Default stream is system-only and hidden. Named streams are what users manage.
    streams = sorted(
        (stream for stream in class_level.streams.all() if not stream.is_default),
        key=lambda stream: stream.name,
    )
    return {
        'id': class_level.id,
        'name': class_level.name,
        'description': class_level.description,
        'order': class_level.order,
        'is_active': class_level.is_active,
        'is_system_generated': class_level.is_system_generated,
        'is_editable': not class_level.is_system_generated,
        'streams': [_serialize_stream(stream) for stream in streams],
        'subjects': [
            _serialize_class_subject(class_subject)
            for class_subject in sorted(
                class_level.class_subjects.all(),
                key=lambda item: item.subject.name,
            )
        ],
    }


def _build_level_subjects(level, class_levels):
    class_subjects_by_subject = {}
    for class_level in class_levels:
        for class_subject in class_level.class_subjects.all():
            class_subjects_by_subject.setdefault(class_subject.subject_id, []).append(
                class_subject,
            )

    subjects = []
    for level_subject in sorted(
        level.level_subjects.all(),
        key=lambda item: item.subject.name,
    ):
        subject = level_subject.subject
        assigned = class_subjects_by_subject.get(subject.id, [])
        groups_by_name = {}
        for class_subject in assigned:
            for group in class_subject.groups.all():
                groups_by_name[group.name] = {
                    'id': group.id,
                    'name': group.name,
                    'is_active': group.is_active,
                }

        subjects.append({
            'id': subject.id,
            'name': subject.name,
            'is_active': subject.is_active and level_subject.is_active,
            'is_system_generated': level_subject.is_system_generated,
            'is_editable': not level_subject.is_system_generated,
            'class_ids': [
                item.class_level_id
                for item in sorted(assigned, key=lambda row: row.class_level.name)
            ],
            'groups': sorted(groups_by_name.values(), key=lambda group: group['name']),
        })

    return subjects


def get_classes_and_subjects_setup(school):
    levels = (
        Level.objects.filter(school=school)
        .prefetch_related(
            'level_subjects__subject',
            'class_levels__streams',
            'class_levels__class_subjects__subject',
            'class_levels__class_subjects__groups',
        )
        .order_by('order', 'name')
    )

    serialized_levels = []
    for level in levels:
        class_levels = sorted(
            level.class_levels.all(),
            key=lambda item: (item.order, item.name),
        )

        serialized_levels.append({
            'id': level.id,
            'name': level.name,
            'description': level.description,
            'order': level.order,
            'is_active': level.is_active,
            'is_system_generated': level.is_system_generated,
            'subject_scope': level.subject_scope,
            'allows_custom_classes': level.allows_custom_classes,
            'classes': [
                _serialize_class_level(class_level)
                for class_level in class_levels
            ],
            'subjects': _build_level_subjects(level, class_levels),
        })

    return serialized_levels


def get_school_level(school, level_id):
    try:
        return Level.objects.get(school=school, id=level_id)
    except Level.DoesNotExist as exc:
        raise NotFound('Level not found.') from exc


def get_school_class_level(school, class_id):
    try:
        return ClassLevel.objects.select_related('level').get(school=school, id=class_id)
    except ClassLevel.DoesNotExist as exc:
        raise NotFound('Class not found.') from exc


def get_school_stream(school, stream_id):
    try:
        return ClassStream.objects.select_related('class_level').get(
            id=stream_id,
            class_level__school=school,
        )
    except ClassStream.DoesNotExist as exc:
        raise NotFound('Stream not found.') from exc


def get_school_class_subject(school, class_subject_id):
    try:
        return ClassSubject.objects.select_related(
            'class_level__level',
            'subject',
        ).get(school=school, id=class_subject_id)
    except ClassSubject.DoesNotExist as exc:
        raise NotFound('Class subject not found.') from exc


def get_school_subject_group(school, group_id):
    try:
        return SubjectGroup.objects.select_related(
            'class_subject__class_level__level',
            'class_subject__subject',
        ).get(
            id=group_id,
            class_subject__school=school,
        )
    except SubjectGroup.DoesNotExist as exc:
        raise NotFound('Subject group not found.') from exc


def get_school_subject(school, subject_id):
    try:
        return Subject.objects.get(school=school, id=subject_id)
    except Subject.DoesNotExist as exc:
        raise NotFound('Subject not found.') from exc


def add_stream(school, *, class_id, name, description=None):
    class_level = get_school_class_level(school, class_id)
    stream = _call(
        curriculum_ops.create_stream,
        school,
        class_level=class_level,
        name=name,
        description=description,
    )
    return _serialize_stream(stream)


def edit_stream(school, *, stream_id, **fields):
    stream = get_school_stream(school, stream_id)
    stream = _call(curriculum_ops.update_stream, stream, **fields)
    return _serialize_stream(stream)


def remove_stream(school, *, stream_id):
    stream = get_school_stream(school, stream_id)
    _call(curriculum_ops.delete_stream, stream)


def add_subject_group(school, *, level_id, subject_id, name):
    level = get_school_level(school, level_id)
    subject = get_school_subject(school, subject_id)
    group = _call(
        curriculum_ops.create_subject_group,
        school,
        level=level,
        subject=subject,
        name=name,
    )
    return {
        'id': group.id,
        'name': group.name,
        'is_active': group.is_active,
    }


def edit_subject_group(school, *, group_id, **fields):
    group = get_school_subject_group(school, group_id)
    group = _call(curriculum_ops.update_subject_group, group, **fields)
    return {
        'id': group.id,
        'name': group.name,
        'is_active': group.is_active,
    }


def remove_subject_group(school, *, group_id):
    group = get_school_subject_group(school, group_id)
    _call(curriculum_ops.delete_subject_group, group)


def add_custom_class(school, *, level_id, name, description=None, order=None):
    level = get_school_level(school, level_id)
    class_level = _call(
        curriculum_ops.create_custom_class_level,
        school,
        level=level,
        name=name,
        description=description,
        order=order,
    )
    class_level = ClassLevel.objects.prefetch_related(
        'streams',
        'class_subjects__subject',
        'class_subjects__groups',
    ).get(pk=class_level.pk)
    return _serialize_class_level(class_level)


def edit_custom_class(school, *, class_id, **fields):
    class_level = get_school_class_level(school, class_id)
    class_level = _call(curriculum_ops.update_custom_class_level, class_level, **fields)
    class_level = ClassLevel.objects.prefetch_related(
        'streams',
        'class_subjects__subject',
        'class_subjects__groups',
    ).get(pk=class_level.pk)
    return _serialize_class_level(class_level)


def remove_custom_class(school, *, class_id):
    class_level = get_school_class_level(school, class_id)
    _call(curriculum_ops.delete_custom_class_level, class_level)


def _subject_response(school, subject):
    assignments = list(
        ClassSubject.objects.filter(school=school, subject=subject)
        .select_related('class_level')
        .order_by('class_level__name'),
    )
    return {
        'id': subject.id,
        'name': subject.name,
        'is_active': subject.is_active,
        'is_system_generated': subject.is_system_generated,
        'is_editable': not subject.is_system_generated,
        'class_ids': [item.class_level_id for item in assignments],
        'assigned_classes': [
            {
                'class_id': item.class_level_id,
                'class_name': item.class_level.name,
                'class_subject_id': item.id,
            }
            for item in assignments
        ],
    }


def add_subject(school, *, level_id, name, class_ids=None):
    level = get_school_level(school, level_id)
    subject = _call(
        curriculum_ops.create_subject_with_assignments,
        school,
        level=level,
        name=name,
        class_ids=class_ids,
    )
    return _subject_response(school, subject)


def edit_subject(school, *, subject_id, name=None, class_ids=None):
    subject = get_school_subject(school, subject_id)
    subject = _call(
        curriculum_ops.update_subject_with_assignments,
        school,
        subject=subject,
        name=name,
        class_ids=class_ids,
    )
    return _subject_response(school, subject)


def remove_subject(school, *, subject_id):
    subject = get_school_subject(school, subject_id)
    _call(curriculum_ops.delete_custom_subject, subject)


def remove_subject_from_class(school, *, class_id, subject_id):
    class_level = get_school_class_level(school, class_id)
    subject = get_school_subject(school, subject_id)
    _call(
        curriculum_ops.remove_subject_from_class,
        school,
        class_level=class_level,
        subject=subject,
    )


def assign_subject_to_class(school, *, class_id, subject_id):
    class_level = get_school_class_level(school, class_id)
    subject = get_school_subject(school, subject_id)
    class_subject = _call(
        curriculum_ops.assign_subject_to_class_strict,
        school,
        class_level=class_level,
        subject=subject,
    )
    class_subject = ClassSubject.objects.select_related('subject').prefetch_related(
        'groups',
    ).get(pk=class_subject.pk)
    return _serialize_class_subject(class_subject)


def set_level_status(school, *, level_id, is_active):
    level = get_school_level(school, level_id)
    level = _call(curriculum_ops.set_level_active, level, is_active=is_active)
    return {
        'id': level.id,
        'name': level.name,
        'is_active': level.is_active,
    }


def set_class_status(school, *, class_id, is_active):
    class_level = get_school_class_level(school, class_id)
    class_level = _call(
        curriculum_ops.set_class_level_active,
        class_level,
        is_active=is_active,
    )
    return {
        'id': class_level.id,
        'name': class_level.name,
        'is_active': class_level.is_active,
    }


def set_subject_status(school, *, subject_id, is_active):
    subject = get_school_subject(school, subject_id)
    subject = _call(curriculum_ops.set_subject_active, subject, is_active=is_active)
    return {
        'id': subject.id,
        'name': subject.name,
        'is_active': subject.is_active,
    }


def validate_classes_and_subjects_ready(school):
    errors = []

    class_levels = (
        ClassLevel.objects.filter(school=school)
        .prefetch_related('streams')
        .order_by('level__order', 'order', 'name')
    )
    for class_level in class_levels:
        custom_streams = [stream for stream in class_level.streams.all() if not stream.is_default]
        if custom_streams and len(custom_streams) < 2:
            errors.append(
                f"Class '{class_level.name}' has only {len(custom_streams)} named stream. "
                'Add at least one more stream, or remove the extra stream.',
            )

    class_subjects = (
        ClassSubject.objects.filter(school=school)
        .select_related('subject', 'class_level')
        .prefetch_related('groups')
        .order_by('class_level__name', 'subject__name')
    )
    seen_level_subjects = set()
    for class_subject in class_subjects:
        level = class_subject.class_level.level
        groups = list(class_subject.groups.all())
        if not groups:
            continue

        key = (level.id, class_subject.subject_id)
        if key in seen_level_subjects:
            continue
        seen_level_subjects.add(key)

        group_names = {
            group.name
            for sibling in ClassSubject.objects.filter(
                class_level__level=level,
                subject_id=class_subject.subject_id,
            ).prefetch_related('groups')
            for group in sibling.groups.all()
        }
        if len(group_names) < 2:
            errors.append(
                f"Subject '{class_subject.subject.name}' in level '{level.name}' "
                f'has only {len(group_names)} group. '
                'Add at least one more group, or remove the extra group.',
            )

    if errors:
        raise ValidationError({'detail': errors})


def complete_classes_and_subjects_setup(school):
    school_setup, _ = SchoolSetup.objects.get_or_create(school=school)
    require_prior_setup_steps(
        school_setup,
        SchoolSetup.SetupStep.CLASSES_AND_SUBJECTS,
    )
    validate_classes_and_subjects_ready(school)
    return advance_setup_if_needed(
        school_setup,
        SchoolSetup.SetupStep.CLASSES_AND_SUBJECTS,
    )
