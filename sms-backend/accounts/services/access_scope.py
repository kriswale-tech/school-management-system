"""Resolve what a membership may see within the active school/term.

Teachers are limited to ClassTeacher + TeachingAssignment rows for the active
term. Other roles operate in school-wide mode (no assignment filter).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from accounts.models import SchoolMembership, User
from schools.models import Term
from teachers.models import ClassTeacher, TeachingAssignment


@dataclass(frozen=True)
class AccessScope:
    """Data visibility for the current membership in one school."""

    mode: str  # 'school' | 'scoped'
    is_class_teacher: bool = False
    is_subject_teacher: bool = False
    class_level_ids: frozenset = field(default_factory=frozenset)
    stream_ids: frozenset = field(default_factory=frozenset)
    # Streams the caller may see (named or default). Empty + scoped => nothing.
    visible_stream_ids: frozenset = field(default_factory=frozenset)
    class_subject_ids: frozenset = field(default_factory=frozenset)

    @property
    def is_scoped(self) -> bool:
        return self.mode == 'scoped'


def _active_term_for_school(school) -> Term | None:
    return Term.objects.filter(school=school, is_active=True).first()


def _empty_scoped(*, is_class_teacher=False, is_subject_teacher=False) -> AccessScope:
    return AccessScope(
        mode='scoped',
        is_class_teacher=is_class_teacher,
        is_subject_teacher=is_subject_teacher,
    )


def _school_wide_scope() -> AccessScope:
    return AccessScope(mode='school')


def resolve_access_scope(membership: SchoolMembership | None) -> AccessScope:
    """Build the access scope for a membership (or empty school-wide if none)."""
    if membership is None:
        return _school_wide_scope()

    if membership.role != User.RoleChoices.TEACHER:
        return _school_wide_scope()

    school = membership.school
    term = _active_term_for_school(school)
    if term is None:
        return _empty_scoped()

    user_id = membership.user_id
    class_level_ids: set = set()
    stream_ids: set = set()
    visible_stream_ids: set = set()
    class_subject_ids: set = set()

    class_teacher_rows = list(
        ClassTeacher.objects.filter(teacher_id=user_id, term=term).only(
            'class_level_id',
            'stream_id',
        )
    )
    teaching_rows = list(
        TeachingAssignment.objects.filter(teacher_id=user_id, term=term).select_related(
            'class_subject',
        )
    )

    is_class_teacher = bool(class_teacher_rows)
    is_subject_teacher = bool(teaching_rows)

    # Whole-class (stream null) assignments expand to every stream of that class.
    whole_class_level_ids: set = set()

    for row in class_teacher_rows:
        class_level_ids.add(row.class_level_id)
        if row.stream_id:
            stream_ids.add(row.stream_id)
            visible_stream_ids.add(row.stream_id)
        else:
            whole_class_level_ids.add(row.class_level_id)

    for row in teaching_rows:
        class_subject_ids.add(row.class_subject_id)
        class_level_id = row.class_subject.class_level_id
        class_level_ids.add(class_level_id)
        if row.stream_id:
            stream_ids.add(row.stream_id)
            visible_stream_ids.add(row.stream_id)
        else:
            whole_class_level_ids.add(class_level_id)

    if whole_class_level_ids:
        from academics.models import ClassStream

        for stream_id in ClassStream.objects.filter(
            class_level_id__in=whole_class_level_ids,
            is_active=True,
        ).values_list('id', flat=True):
            visible_stream_ids.add(stream_id)

    return AccessScope(
        mode='scoped',
        is_class_teacher=is_class_teacher,
        is_subject_teacher=is_subject_teacher,
        class_level_ids=frozenset(class_level_ids),
        stream_ids=frozenset(stream_ids),
        visible_stream_ids=frozenset(visible_stream_ids),
        class_subject_ids=frozenset(class_subject_ids),
    )


def filter_class_list_results(results: list[dict], scope: AccessScope) -> list[dict]:
    """Keep class-list stream rows the membership is allowed to see."""
    if not scope.is_scoped:
        return results
    allowed = {str(stream_id) for stream_id in scope.visible_stream_ids}
    return [row for row in results if str(row.get('id')) in allowed]
