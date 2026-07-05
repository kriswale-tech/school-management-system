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
        'streams': [_serialize_stream(stream) for stream in streams],
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

    return {
        'levels': [
            {
                'id': level.id,
                'name': level.name,
                'description': level.description,
                'order': level.order,
                'is_active': level.is_active,
                'classes': [
                    _serialize_class_level(class_level)
                    for class_level in sorted(
                        level.class_levels.all(),
                        key=lambda item: (item.order, item.name),
                    )
                ],
                'subjects': _build_level_subjects(level.class_levels.all()),
            }
            for level in levels
        ],
    }
