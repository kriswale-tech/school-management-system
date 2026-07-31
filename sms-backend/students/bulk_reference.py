from dataclasses import dataclass, field

from academics.models import ClassStream
from academics.services.all_classes import get_all_classes


def _normalize(value: str | None) -> str:
    if not value:
        return ''
    return ' '.join(str(value).strip().lower().split())


@dataclass
class StudentBulkReferenceRow:
    level_name: str
    class_name: str
    stream_name: str = ''


@dataclass
class StudentBulkReferenceContext:
    term_id: str
    class_names: list[str] = field(default_factory=list)
    stream_names: list[str] = field(default_factory=list)
    gender_values: list[str] = field(default_factory=list)
    relationship_values: list[str] = field(default_factory=list)
    is_new_student_values: list[str] = field(default_factory=list)
    reference_rows: list[StudentBulkReferenceRow] = field(default_factory=list)
    streams_by_display_name: dict[str, list[ClassStream]] = field(default_factory=dict)
    streams_by_class_and_stream: dict[tuple[str, str], ClassStream] = field(default_factory=dict)
    default_streams_by_class: dict[str, ClassStream] = field(default_factory=dict)

    def resolve_stream(
        self,
        class_name: str,
        stream_name: str = '',
    ) -> tuple[ClassStream | None, str | None]:
        if not class_name:
            return None, 'class_name is required.'

        normalized_class = _normalize(class_name)
        normalized_stream = _normalize(stream_name)

        if normalized_stream:
            stream = self.streams_by_class_and_stream.get((normalized_class, normalized_stream))
            if stream is not None:
                return stream, None

            # Allow display_name in class_name even when stream_name is also set.
            matches = self.streams_by_display_name.get(normalized_class, [])
            if len(matches) == 1:
                return matches[0], None

            suggestion = _suggest_name(stream_name, self.stream_names)
            message = f'Stream "{stream_name}" not found for class "{class_name}".'
            if suggestion:
                message = f'{message} Did you mean "{suggestion}"?'
            return None, message

        matches = self.streams_by_display_name.get(normalized_class, [])
        if len(matches) == 1:
            return matches[0], None
        if len(matches) > 1:
            return None, (
                f'Class "{class_name}" matches multiple streams. '
                'Use the exact class name from the Reference sheet.'
            )

        default = self.default_streams_by_class.get(normalized_class)
        if default is not None:
            return default, None

        suggestion = _suggest_name(class_name, self.class_names)
        message = f'Class "{class_name}" not found.'
        if suggestion:
            message = f'{message} Did you mean "{suggestion}"?'
        return None, message


def build_student_bulk_reference_context(school) -> StudentBulkReferenceContext:
    from students.models import Student, StudentParent

    payload = get_all_classes(school=school)
    context = StudentBulkReferenceContext(
        term_id=str(payload['term_id']),
        gender_values=[choice.value for choice in Student.GenderChoices],
        relationship_values=[choice.value for choice in StudentParent.RelationshipChoices],
        is_new_student_values=['true', 'false'],
    )

    class_names: set[str] = set()
    stream_names: set[str] = set()

    for level in payload['levels']:
        for entry in level['classes']:
            stream = ClassStream.objects.select_related('class_level').get(id=entry['id'])
            display_name = entry['display_name']
            class_level_name = stream.class_level.name
            stream_label = '' if entry['is_default'] else (stream.name or '')

            class_names.add(display_name)
            if stream_label:
                stream_names.add(stream_label)

            context.reference_rows.append(
                StudentBulkReferenceRow(
                    level_name=level['name'],
                    class_name=display_name,
                    stream_name=stream_label,
                ),
            )

            display_key = _normalize(display_name)
            context.streams_by_display_name.setdefault(display_key, []).append(stream)

            class_key = _normalize(class_level_name)
            if entry['is_default']:
                context.default_streams_by_class[class_key] = stream
            else:
                context.streams_by_class_and_stream[(class_key, _normalize(stream_label))] = stream
                context.streams_by_class_and_stream[
                    (class_key, _normalize(stream.full_name))
                ] = stream

    context.class_names = sorted(class_names)
    context.stream_names = sorted(stream_names)
    return context


def _suggest_name(value: str, options: list[str]) -> str | None:
    normalized = _normalize(value)
    if not normalized:
        return None
    for option in options:
        if _normalize(option) == normalized:
            return option
    for option in options:
        if normalized in _normalize(option) or _normalize(option) in normalized:
            return option
    return None
