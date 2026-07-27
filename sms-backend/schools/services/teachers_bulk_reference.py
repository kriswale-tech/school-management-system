from dataclasses import dataclass, field

from academics.models import ClassLevel, ClassSubject, ClassStream, SubjectGroup
from schools.services.teachers import _get_active_term


def _normalize(value: str | None) -> str:
    if not value:
        return ''
    return ' '.join(str(value).strip().lower().split())


@dataclass
class TeacherBulkReferenceRow:
    class_name: str
    subject_name: str = ''
    stream_name: str = ''
    subject_group_name: str = ''


@dataclass
class TeacherBulkReferenceContext:
    term_id: str
    class_names: list[str] = field(default_factory=list)
    subject_names: list[str] = field(default_factory=list)
    stream_names: list[str] = field(default_factory=list)
    subject_group_names: list[str] = field(default_factory=list)
    reference_rows: list[TeacherBulkReferenceRow] = field(default_factory=list)
    classes_by_name: dict[str, list[ClassLevel]] = field(default_factory=dict)
    class_subjects_by_key: dict[tuple[str, str], ClassSubject] = field(default_factory=dict)
    streams_by_key: dict[tuple[str, str], ClassStream] = field(default_factory=dict)
    subject_groups_by_key: dict[tuple[str, str, str], SubjectGroup] = field(default_factory=dict)

    def resolve_class_level(self, class_name: str) -> tuple[ClassLevel | None, str | None]:
        normalized = _normalize(class_name)
        matches = self.classes_by_name.get(normalized, [])
        if not matches:
            return None, f'Class "{class_name}" not found.'
        if len(matches) > 1:
            return None, f'Class "{class_name}" is ambiguous across levels.'
        return matches[0], None

    def resolve_class_subject(
        self,
        class_name: str,
        subject_name: str,
    ) -> tuple[ClassSubject | None, str | None]:
        class_level, class_error = self.resolve_class_level(class_name)
        if class_error:
            return None, class_error

        normalized_subject = _normalize(subject_name)
        class_subject = self.class_subjects_by_key.get(
            (_normalize(class_level.name), normalized_subject),
        )
        if class_subject is None:
            suggestion = _suggest_name(subject_name, self.subject_names)
            message = f'Subject "{subject_name}" not found for class "{class_name}".'
            if suggestion:
                message = f'{message} Did you mean "{suggestion}"?'
            return None, message
        return class_subject, None

    def resolve_stream(
        self,
        class_level: ClassLevel,
        stream_name: str | None,
    ) -> tuple[ClassStream | None, str | None]:
        if not stream_name:
            return None, None

        stream = self.streams_by_key.get(
            (_normalize(class_level.name), _normalize(stream_name)),
        )
        if stream is None:
            suggestion = _suggest_name(stream_name, self.stream_names)
            message = f'Stream "{stream_name}" not found for class "{class_level.name}".'
            if suggestion:
                message = f'{message} Did you mean "{suggestion}"?'
            return None, message
        return stream, None

    def resolve_subject_group(
        self,
        class_name: str,
        subject_name: str,
        subject_group_name: str | None,
    ) -> tuple[SubjectGroup | None, str | None]:
        if not subject_group_name:
            return None, None

        subject_group = self.subject_groups_by_key.get(
            (
                _normalize(class_name),
                _normalize(subject_name),
                _normalize(subject_group_name),
            ),
        )
        if subject_group is None:
            suggestion = _suggest_name(subject_group_name, self.subject_group_names)
            message = (
                f'Subject group "{subject_group_name}" not found for '
                f'{class_name} {subject_name}.'
            )
            if suggestion:
                message = f'{message} Did you mean "{suggestion}"?'
            return None, message
        return subject_group, None


def _suggest_name(value: str, options: list[str]) -> str | None:
    import difflib

    normalized = _normalize(value)
    lookup = {_normalize(option): option for option in options}
    matches = difflib.get_close_matches(normalized, lookup.keys(), n=1, cutoff=0.75)
    if not matches:
        return None
    return lookup[matches[0]]


def build_teacher_bulk_reference_context(school) -> TeacherBulkReferenceContext:
    term = _get_active_term(school)
    context = TeacherBulkReferenceContext(term_id=str(term.id))

    class_levels = (
        ClassLevel.objects.filter(school=school, is_active=True, level__is_active=True)
        .select_related('level')
        .prefetch_related('streams', 'class_subjects__subject', 'class_subjects__groups')
        .order_by('level__order', 'order', 'name')
    )

    class_name_set: set[str] = set()
    subject_name_set: set[str] = set()
    stream_name_set: set[str] = set()
    subject_group_name_set: set[str] = set()

    for class_level in class_levels:
        normalized_class_name = _normalize(class_level.name)
        context.classes_by_name.setdefault(normalized_class_name, []).append(class_level)
        class_name_set.add(class_level.name)

        for stream in class_level.streams.all():
            if stream.is_default or not stream.is_active:
                continue
            stream_name_set.add(stream.name)
            context.streams_by_key[(_normalize(class_level.name), _normalize(stream.name))] = stream
            context.reference_rows.append(
                TeacherBulkReferenceRow(
                    class_name=class_level.name,
                    stream_name=stream.name,
                ),
            )

        for class_subject in class_level.class_subjects.all():
            if not class_subject.is_active:
                continue

            subject_name = class_subject.subject.name
            subject_name_set.add(subject_name)
            context.class_subjects_by_key[
                (_normalize(class_level.name), _normalize(subject_name))
            ] = class_subject
            context.reference_rows.append(
                TeacherBulkReferenceRow(
                    class_name=class_level.name,
                    subject_name=subject_name,
                ),
            )

            for group in class_subject.groups.all():
                if not group.is_active:
                    continue
                subject_group_name_set.add(group.name)
                context.subject_groups_by_key[
                    (
                        _normalize(class_level.name),
                        _normalize(subject_name),
                        _normalize(group.name),
                    )
                ] = group
                context.reference_rows.append(
                    TeacherBulkReferenceRow(
                        class_name=class_level.name,
                        subject_name=subject_name,
                        subject_group_name=group.name,
                    ),
                )

    context.class_names = sorted(class_name_set, key=str.casefold)
    context.subject_names = sorted(subject_name_set, key=str.casefold)
    context.stream_names = sorted(stream_name_set, key=str.casefold)
    context.subject_group_names = sorted(subject_group_name_set, key=str.casefold)
    return context
