from academics.models import Level


def _serialize_stream(stream):
    return {
        'id': stream.id,
        'name': stream.name,
        'full_name': stream.full_name,
        'description': stream.description,
        'is_default': stream.is_default,
        'is_active': stream.is_active,
        'capacity': stream.capacity,
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
    streams = sorted(
        class_level.streams.all(),
        key=lambda stream: (not stream.is_default, stream.name),
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


def _build_level_subjects(class_levels):
    subjects_by_id = {}
    groups_by_subject = {}

    for class_level in class_levels:
        for class_subject in class_level.class_subjects.all():
            subject = class_subject.subject
            if subject.id not in subjects_by_id:
                subjects_by_id[subject.id] = {
                    'id': subject.id,
                    'name': subject.name,
                    'is_active': subject.is_active,
                    'is_system_generated': subject.is_system_generated,
                    'is_editable': not subject.is_system_generated,
                }
                groups_by_subject[subject.id] = {}

            for group in class_subject.groups.all():
                groups_by_subject[subject.id][group.name] = {
                    'id': group.id,
                    'name': group.name,
                    'is_active': group.is_active,
                }

    subjects = []
    for subject_id, subject_data in subjects_by_id.items():
        groups = sorted(
            groups_by_subject[subject_id].values(),
            key=lambda group: group['name'],
        )
        subjects.append({
            **subject_data,
            'groups': groups,
        })

    subjects.sort(key=lambda subject: subject['name'])
    return subjects


def get_classes_and_subjects_setup(school):
    levels = (
        Level.objects.filter(school=school)
        .prefetch_related(
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
            'subjects': _build_level_subjects(class_levels),
        })

    return serialized_levels
