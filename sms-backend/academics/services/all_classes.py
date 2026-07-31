from django.db.models import Count, Q

from academics.models import ClassStream, Level
from students.services import get_active_term


def get_all_classes(*, school, term=None):
    """Levels with flat selectable class entries (each id is a stream UUID).

    Named streams become separate entries. Classes with only a default stream
    expose that default stream as a single entry using the class display name.
    """
    term = term or get_active_term(
        school,
        detail='Set an active term before viewing class options.',
    )

    levels = (
        Level.objects.filter(school=school, is_active=True)
        .prefetch_related('class_levels__streams')
        .order_by('order', 'name')
    )

    stream_counts = {
        row['id']: row['student_count']
        for row in ClassStream.objects.filter(
            class_level__school=school,
        ).annotate(
            student_count=Count(
                'enrollments',
                filter=Q(enrollments__term=term),
            ),
        ).values('id', 'student_count')
    }

    result = []
    for level in levels:
        classes_payload = []
        class_levels = sorted(
            (cl for cl in level.class_levels.all() if cl.is_active),
            key=lambda item: (item.order, item.name),
        )
        for class_level in class_levels:
            streams = [s for s in class_level.streams.all() if s.is_active]
            named = sorted(
                (s for s in streams if not s.is_default),
                key=lambda item: item.name,
            )
            default = next((s for s in streams if s.is_default), None)

            if named:
                for stream in named:
                    classes_payload.append({
                        'id': stream.id,
                        'class_level_id': class_level.id,
                        'display_name': stream.full_name,
                        'student_count': stream_counts.get(stream.id, 0),
                        'is_default': False,
                    })
            elif default is not None:
                classes_payload.append({
                    'id': default.id,
                    'class_level_id': class_level.id,
                    'display_name': class_level.name,
                    'student_count': stream_counts.get(default.id, 0),
                    'is_default': True,
                })

        result.append({
            'id': level.id,
            'name': level.name,
            'order': level.order,
            'classes': classes_payload,
        })

    return {
        'term_id': term.id,
        'levels': result,
    }
