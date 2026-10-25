"""Curated academic insights for Reports & Insights."""

from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
from uuid import UUID

from rest_framework.exceptions import NotFound, ValidationError

from academics.models import ClassLevel, ClassStream, Level, LevelSubject
from accounts.services.access_scope import resolve_access_scope
from assessments.models import AssessmentConfig
from reports.services.scoring_bulk import (
    DEFAULT_PASS_MARK,
    average_or_none,
    collect_published_scores,
    pass_rate,
    student_overall_averages,
)
from schools.models import Term
from students.models import Student
from students.services import get_active_term


def _term_label(term) -> str:
    return f'{term.academic_year.academic_year} · {term.get_term_display()}'


def _resolve_term(*, school, term_id=None):
    if term_id:
        term = (
            Term.objects.filter(id=term_id, school=school)
            .select_related('academic_year')
            .first()
        )
        if term is None:
            raise NotFound('Term not found.')
        return term
    return get_active_term(school, detail='Set an active term before viewing reports.')


def _resolve_compare_term(*, school, term, compare_term_id=None):
    if not compare_term_id:
        return None
    if str(compare_term_id) == str(term.id):
        raise ValidationError({'compare_term_id': 'Compare term must differ from the selected term.'})
    compare = (
        Term.objects.filter(id=compare_term_id, school=school)
        .select_related('academic_year')
        .first()
    )
    if compare is None:
        raise NotFound('Compare term not found.')
    return compare


def _scope_for_membership(membership):
    return resolve_access_scope(membership)


def _enrollment_queryset(*, term, scope=None, class_level_id=None, level_id=None, stream_id=None):
    """Active-term enrollments, optionally narrowed by scope / class / level / stream."""
    from students.models import ClassEnrollment

    qs = ClassEnrollment.objects.filter(term=term).select_related(
        'stream',
        'class_level',
        'class_level__level',
    )
    if class_level_id:
        qs = qs.filter(class_level_id=class_level_id)
    if level_id:
        qs = qs.filter(class_level__level_id=level_id)
    if stream_id:
        qs = qs.filter(stream_id=stream_id)
    if scope is not None and scope.is_scoped and scope.visible_stream_ids:
        qs = qs.filter(stream_id__in=scope.visible_stream_ids)
    return qs


def _count_enrolled(*, term, scope=None, class_level_id=None, level_id=None, stream_id=None) -> int:
    return _enrollment_queryset(
        term=term,
        scope=scope,
        class_level_id=class_level_id,
        level_id=level_id,
        stream_id=stream_id,
    ).count()


def _enrollment_size_maps(*, term, scope=None, class_level_id=None, level_id=None):
    """
    Enrollment headcounts for the term.

    Returns:
      by_key: {(class_level_id, stream_id): count}
      by_display: {display_name: count}
      total: int
    """
    by_key: dict[tuple, int] = defaultdict(int)
    by_display: dict[str, int] = defaultdict(int)
    for row in _enrollment_queryset(
        term=term,
        scope=scope,
        class_level_id=class_level_id,
        level_id=level_id,
    ):
        key = (row.class_level_id, row.stream_id)
        by_key[key] += 1
        label = row.stream.full_name if row.stream_id else row.class_level.name
        by_display[label] += 1
    return {
        'by_key': dict(by_key),
        'by_display': dict(by_display),
        'total': sum(by_key.values()),
    }


def _dominant_pass_mark(rows, pass_marks: dict[UUID, Decimal]) -> Decimal:
    if not rows:
        return DEFAULT_PASS_MARK
    counts: Counter = Counter(row.level_id for row in rows)
    level_id = counts.most_common(1)[0][0]
    return pass_marks.get(level_id, DEFAULT_PASS_MARK)


def _kpis_from_rows(rows, pass_marks: dict[UUID, Decimal]) -> dict:
    overall = student_overall_averages(rows)
    overall_values = list(overall.values())
    subject_values = [row.total for row in rows]
    pass_mark = _dominant_pass_mark(rows, pass_marks)
    return {
        'students_with_results': len(overall_values),
        'published_subject_scores': len(rows),
        'average_score': average_or_none(overall_values),
        'subject_average': average_or_none(subject_values),
        'pass_rate': pass_rate(overall_values, pass_mark),
        'pass_mark': float(pass_mark),
    }


def _delta(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None:
        return None
    return round(current - previous, 1)


def _list_terms_payload(*, school) -> list[dict]:
    terms = (
        Term.objects.filter(school=school)
        .select_related('academic_year')
        .order_by('-start_date', '-id')
    )
    return [
        {
            'id': str(term.id),
            'label': _term_label(term),
            'is_active': term.is_active,
        }
        for term in terms
    ]


def _academic_structure_stats(*, school, term, scope) -> dict:
    """Classes / subjects / subject–class slots for academic insight headers."""
    from academics.models import ClassSubject, ClassStream
    from academics.services.classes import get_class_stats
    from teachers.models import TeachingAssignment

    class_stats = get_class_stats(school=school, term=term, scope=scope)
    class_subject_qs = ClassSubject.objects.filter(
        school=school,
        is_active=True,
        class_level__is_active=True,
    )
    teaching_qs = TeachingAssignment.objects.filter(term=term)

    if scope.is_scoped and scope.visible_stream_ids:
        class_level_ids = set(
            ClassStream.objects.filter(id__in=scope.visible_stream_ids).values_list(
                'class_level_id',
                flat=True,
            )
        )
        class_subject_qs = class_subject_qs.filter(class_level_id__in=class_level_ids)
        teaching_qs = teaching_qs.filter(stream_id__in=scope.visible_stream_ids)

    return {
        'classes_count': class_stats['total_classes'],
        'distinct_subjects_count': class_subject_qs.values('subject_id').distinct().count(),
        'class_subjects_count': class_stats['total_class_subjects'],
        'teaching_assignments_count': teaching_qs.count(),
        'unassigned_class_subjects': class_stats['unassigned_class_subjects'],
    }


def get_overview(*, school, membership, term_id=None, compare_term_id=None, level_id=None, class_level_id=None):
    term = _resolve_term(school=school, term_id=term_id)
    compare_term = _resolve_compare_term(school=school, term=term, compare_term_id=compare_term_id)
    scope = _scope_for_membership(membership)

    rows, pass_marks = collect_published_scores(
        school=school,
        term=term,
        scope=scope,
        class_level_id=class_level_id,
        level_id=level_id,
    )
    kpis = _kpis_from_rows(rows, pass_marks)
    students_count = _count_enrolled(
        term=term,
        scope=scope,
        class_level_id=class_level_id,
        level_id=level_id,
    )
    structure = _academic_structure_stats(school=school, term=term, scope=scope)

    compare = None
    if compare_term is not None:
        compare_rows, compare_pass = collect_published_scores(
            school=school,
            term=compare_term,
            scope=scope,
            class_level_id=class_level_id,
            level_id=level_id,
        )
        compare_kpis = _kpis_from_rows(compare_rows, compare_pass)
        compare = {
            'term_id': str(compare_term.id),
            'term_label': _term_label(compare_term),
            **compare_kpis,
            'students_count': _count_enrolled(
                term=compare_term,
                scope=scope,
                class_level_id=class_level_id,
                level_id=level_id,
            ),
            'average_score_delta': _delta(kpis['average_score'], compare_kpis['average_score']),
            'pass_rate_delta': _delta(kpis['pass_rate'], compare_kpis['pass_rate']),
        }

    return {
        'term_id': str(term.id),
        'term_label': _term_label(term),
        'terms': _list_terms_payload(school=school),
        'scope_mode': scope.mode,
        **kpis,
        'students_count': students_count,
        **structure,
        'compare': compare,
    }


def _class_sort_keys(*, school, class_level_ids: set) -> dict[str, tuple]:
    """Curriculum order: level.order → class.order → stream name."""
    if not class_level_ids:
        return {}
    class_levels = {
        str(row.id): row
        for row in ClassLevel.objects.filter(
            school=school,
            id__in=class_level_ids,
        ).select_related('level')
    }
    streams = {
        str(row.id): row
        for row in ClassStream.objects.filter(class_level_id__in=class_level_ids)
    }

    keys: dict[str, tuple] = {}
    for class_level_id, class_level in class_levels.items():
        keys[class_level_id] = (
            class_level.level.order,
            class_level.order,
            class_level.name.lower(),
        )
    # stream sort helpers keyed by stream id
    for stream_id, stream in streams.items():
        class_key = keys.get(str(stream.class_level_id), (999, 999, ''))
        keys[f'stream:{stream_id}'] = (
            *class_key,
            0 if stream.is_default else 1,
            stream.name.lower(),
        )
    return keys


def get_by_class(*, school, membership, term_id=None, level_id=None, class_level_id=None):
    term = _resolve_term(school=school, term_id=term_id)
    scope = _scope_for_membership(membership)
    rows, pass_marks = collect_published_scores(
        school=school,
        term=term,
        scope=scope,
        class_level_id=class_level_id,
        level_id=level_id,
    )
    enrollment = _enrollment_size_maps(
        term=term,
        scope=scope,
        class_level_id=class_level_id,
        level_id=level_id,
    )

    by_class: dict[tuple, list] = defaultdict(list)
    meta_by_key: dict[tuple, tuple] = {}
    for row in rows:
        key = (row.class_level_id, row.stream_id)
        by_class[key].append(row)
        meta_by_key[key] = (row.class_display_name, row.level_id)

    # Include enrolled classes with no published scores yet.
    for enroll in _enrollment_queryset(
        term=term,
        scope=scope,
        class_level_id=class_level_id,
        level_id=level_id,
    ):
        key = (enroll.class_level_id, enroll.stream_id)
        if key in meta_by_key:
            continue
        display_name = (
            enroll.stream.full_name if enroll.stream_id else enroll.class_level.name
        )
        meta_by_key[key] = (display_name, enroll.class_level.level_id)
        by_class.setdefault(key, [])

    sort_keys = _class_sort_keys(
        school=school,
        class_level_ids={key[0] for key in by_class},
    )

    results = []
    for (class_level_id_val, stream_id), class_rows in by_class.items():
        display_name, level_id_val = meta_by_key[(class_level_id_val, stream_id)]
        overall = student_overall_averages(class_rows)
        overall_values = list(overall.values())
        pass_mark = pass_marks.get(level_id_val, DEFAULT_PASS_MARK)
        class_key = sort_keys.get(str(class_level_id_val), (999, 999, display_name.lower()))
        if stream_id:
            stream_key = sort_keys.get(
                f'stream:{stream_id}',
                (*class_key, 1, ''),
            )
        else:
            stream_key = (*class_key, 0, '')
        students_count = enrollment['by_key'].get((class_level_id_val, stream_id), 0)
        results.append({
            'class_level_id': str(class_level_id_val),
            'stream_id': str(stream_id) if stream_id else None,
            'display_name': display_name,
            'students_count': students_count,
            'students_with_results': len(overall_values),
            'published_subject_scores': len(class_rows),
            'average_score': average_or_none(overall_values),
            'pass_rate': pass_rate(overall_values, pass_mark),
            '_sort': stream_key,
        })

    results.sort(key=lambda item: item['_sort'])
    for item in results:
        item.pop('_sort', None)
    return {
        'term_id': str(term.id),
        'term_label': _term_label(term),
        'students_count': enrollment['total'],
        'students_with_results': sum(item['students_with_results'] for item in results),
        'results': results,
    }


def get_by_subject(*, school, membership, term_id=None, level_id=None, class_level_id=None):
    term = _resolve_term(school=school, term_id=term_id)
    scope = _scope_for_membership(membership)
    rows, pass_marks = collect_published_scores(
        school=school,
        term=term,
        scope=scope,
        class_level_id=class_level_id,
        level_id=level_id,
    )

    by_subject: dict[tuple, list] = defaultdict(list)
    for row in rows:
        key = (row.subject_id, row.subject_name, row.level_id)
        by_subject[key].append(row)

    results = []
    for (subject_id, subject_name, level_id_val), subject_rows in by_subject.items():
        totals = [row.total for row in subject_rows]
        pass_mark = pass_marks.get(level_id_val, DEFAULT_PASS_MARK)
        results.append({
            'subject_id': str(subject_id),
            'subject_name': subject_name,
            'score_count': len(totals),
            'average_score': average_or_none(totals),
            'pass_rate': pass_rate(totals, pass_mark),
        })

    results.sort(key=lambda item: (-(item['average_score'] or 0), item['subject_name'].lower()))
    return {
        'term_id': str(term.id),
        'term_label': _term_label(term),
        'results': results,
    }


def _score_band_specs(pass_mark: Decimal) -> list[tuple[Decimal, Decimal, str]]:
    """Build inclusive score ranges for position-only distribution pies."""
    try:
        pm = int(pass_mark)
    except (TypeError, ValueError):
        pm = 40
    pm = max(0, min(100, pm))

    bands: list[tuple[Decimal, Decimal, str]] = []
    if pm > 0:
        bands.append((Decimal(0), Decimal(pm - 1), f'Below {pm}'))

    cursor = pm
    for upper in (59, 79, 100):
        if cursor > 100:
            break
        if cursor > upper:
            continue
        high = upper
        low = cursor
        label = f'{low}–{high}' if low != high else str(low)
        bands.append((Decimal(low), Decimal(high), label))
        cursor = high + 1
    return bands


def _bucket_total(total: Decimal, bands: list[tuple[Decimal, Decimal, str]]) -> str:
    for low, high, label in bands:
        if low <= total <= high:
            return label
    if bands:
        return bands[-1][2]
    return 'Other'


def _distribution_results(counts: Counter, band_order: list[str], total: int) -> list[dict]:
    results = []
    for label in band_order:
        count = counts.get(label, 0)
        results.append({
            'grade': label,
            'count': count,
            'percent': round(100.0 * count / total, 1) if total else 0.0,
        })
    for label, count in counts.items():
        if label in band_order:
            continue
        results.append({
            'grade': label,
            'count': count,
            'percent': round(100.0 * count / total, 1) if total else 0.0,
        })
    return results


def get_grade_distribution(*, school, membership, term_id=None, level_id=None, class_level_id=None):
    """
    Distribution pie for one class.

    Grade / grade+position configs use letter/number bands.
    Position-only configs use score ranges (same pie shape) with mode=score_bands.
    """
    if not class_level_id:
        raise ValidationError({
            'class_level_id': 'Select a class to view the distribution.',
        })

    term = _resolve_term(school=school, term_id=term_id)
    scope = _scope_for_membership(membership)
    class_level = (
        ClassLevel.objects.filter(school=school, id=class_level_id, is_active=True)
        .select_related('level')
        .first()
    )
    if class_level is None:
        raise NotFound('Class not found.')

    # Ignore stale level_id from older clients; class alone scopes the data.
    rows, pass_marks = collect_published_scores(
        school=school,
        term=term,
        scope=scope,
        class_level_id=class_level_id,
    )

    config = (
        AssessmentConfig.objects.filter(
            term_id=term.id,
            level_id=class_level.level_id,
        )
        .prefetch_related('grade_bands')
        .first()
    )
    uses_grades = config.uses_grades() if config is not None else True
    pass_mark = pass_marks.get(class_level.level_id, DEFAULT_PASS_MARK)
    if config is not None and config.pass_mark is not None:
        pass_mark = Decimal(config.pass_mark)

    counts: Counter = Counter()
    total = 0

    if uses_grades:
        mode = 'grades'
        for row in rows:
            if row.grade:
                counts[row.grade] += 1
                total += 1
        band_order = (
            [band.grade for band in config.grade_bands.all()]
            if config is not None
            else sorted(counts.keys())
        )
    else:
        mode = 'score_bands'
        bands = _score_band_specs(pass_mark)
        band_order = [label for _low, _high, label in bands]
        for row in rows:
            counts[_bucket_total(row.total, bands)] += 1
            total += 1

    students_count = _count_enrolled(
        term=term,
        scope=scope,
        class_level_id=class_level.id,
    )
    students_with_results = len({row.student_id for row in rows})

    return {
        'term_id': str(term.id),
        'term_label': _term_label(term),
        'class_level_id': str(class_level.id),
        'class_level_name': class_level.name,
        'level_id': str(class_level.level_id),
        'level_name': class_level.level.name,
        'mode': mode,
        'result_type': (
            config.result_type
            if config is not None
            else AssessmentConfig.ResultType.GRADE_AND_POSITION
        ),
        'pass_mark': float(pass_mark),
        'students_count': students_count,
        'students_with_results': students_with_results,
        'total_graded': total,
        'results': _distribution_results(counts, band_order, total),
    }


def get_filter_options(*, school, membership) -> dict:
    """Terms, levels, and classes available for report filters (scope-aware)."""
    scope = _scope_for_membership(membership)
    active = Term.objects.filter(school=school, is_active=True).first()
    levels_qs = Level.objects.filter(school=school, is_active=True).order_by('order', 'name')
    classes_qs = ClassLevel.objects.filter(school=school, is_active=True).select_related(
        'level',
    ).order_by('level__order', 'order', 'name')

    if scope.is_scoped:
        if scope.class_level_ids:
            classes_qs = classes_qs.filter(id__in=scope.class_level_ids)
            level_ids = set(classes_qs.values_list('level_id', flat=True))
            levels_qs = levels_qs.filter(id__in=level_ids)
        else:
            classes_qs = classes_qs.none()
            levels_qs = levels_qs.none()

    return {
        'active_term_id': str(active.id) if active else None,
        'terms': _list_terms_payload(school=school),
        'levels': [{'id': str(level.id), 'name': level.name} for level in levels_qs],
        'class_levels': [
            {
                'id': str(row.id),
                'name': row.name,
                'level_id': str(row.level_id),
            }
            for row in classes_qs
        ],
    }


def get_subject_heatmap(*, school, membership, term_id=None, level_id=None, class_level_id=None):
    """Class × subject matrix for one level (required), curriculum-ordered."""
    if not level_id:
        raise ValidationError({
            'level_id': 'Select a level. Subject sets differ by level and cannot be mixed.',
        })

    term = _resolve_term(school=school, term_id=term_id)
    scope = _scope_for_membership(membership)
    level = Level.objects.filter(school=school, id=level_id, is_active=True).first()
    if level is None:
        raise NotFound('Level not found.')

    class_levels_qs = ClassLevel.objects.filter(
        school=school,
        level_id=level_id,
        is_active=True,
    ).order_by('order', 'name')
    if class_level_id:
        class_levels_qs = class_levels_qs.filter(id=class_level_id)
    if scope.is_scoped and scope.class_level_ids:
        class_levels_qs = class_levels_qs.filter(id__in=scope.class_level_ids)

    class_levels = list(class_levels_qs)

    # Curriculum streams in display order (named first, else default) — same as assessments.
    class_labels: list[str] = []
    for class_level in class_levels:
        streams = list(
            ClassStream.objects.filter(class_level=class_level, is_active=True)
        )
        named = sorted(
            (stream for stream in streams if not stream.is_default),
            key=lambda item: item.name,
        )
        default = next((stream for stream in streams if stream.is_default), None)
        chosen = named or ([default] if default is not None else [])
        for stream in chosen:
            class_labels.append(stream.full_name)

    subjects = list(
        LevelSubject.objects.filter(
            school=school,
            level_id=level_id,
            is_active=True,
        )
        .select_related('subject')
        .order_by('subject__name')
    )
    subject_names = [row.subject.name for row in subjects]
    subject_ids = {row.subject_id for row in subjects}

    rows, _pass_marks = collect_published_scores(
        school=school,
        term=term,
        scope=scope,
        class_level_id=class_level_id,
        level_id=level_id,
    )

    bucket: dict[tuple[str, str], list[Decimal]] = defaultdict(list)
    for row in rows:
        if row.subject_id not in subject_ids:
            continue
        bucket[(row.class_display_name, row.subject_name)].append(row.total)

    # Prefer curriculum class labels; fall back to any labels present in scores.
    if not class_labels:
        class_labels = sorted({key[0] for key in bucket})

    enrollment = _enrollment_size_maps(
        term=term,
        scope=scope,
        class_level_id=class_level_id,
        level_id=level_id,
    )
    class_sizes = [
        {
            'display_name': class_name,
            'students_count': enrollment['by_display'].get(class_name, 0),
        }
        for class_name in class_labels
    ]

    cells = []
    for class_name in class_labels:
        for subject_name in subject_names:
            values = bucket.get((class_name, subject_name), [])
            cells.append({
                'class_display_name': class_name,
                'subject_name': subject_name,
                'average_score': average_or_none(values),
                'score_count': len(values),
            })

    return {
        'term_id': str(term.id),
        'term_label': _term_label(term),
        'level_id': str(level.id),
        'level_name': level.name,
        'students_count': enrollment['total'],
        'classes': class_labels,
        'class_sizes': class_sizes,
        'subjects': subject_names,
        'cells': cells,
    }


def get_workflow(*, school, membership, term_id=None, level_id=None):
    """Assessment workflow progress (pending → ready → released)."""
    term = _resolve_term(school=school, term_id=term_id)
    scope = _scope_for_membership(membership)

    from assessments.services.admin_overview import list_admin_assessment_overview

    assessment = list_admin_assessment_overview(school=school, term_id=term.id)
    rows = assessment['results']

    if scope.is_scoped and scope.class_level_ids:
        allowed = {str(cid) for cid in scope.class_level_ids}
        rows = [row for row in rows if row['class_level_id'] in allowed]

    if level_id:
        level_class_ids = {
            str(cid)
            for cid in ClassLevel.objects.filter(
                school=school,
                level_id=level_id,
                is_active=True,
            ).values_list('id', flat=True)
        }
        rows = [row for row in rows if row['class_level_id'] in level_class_ids]

    pending = sum(row['with_class_teacher_count'] for row in rows)
    ready = sum(row['ready_for_you_count'] for row in rows)
    released = sum(row['released_count'] for row in rows)
    needs_correction = sum(row['needs_correction_count'] for row in rows)
    total_students = sum(row['students_count'] for row in rows)
    completed = ready + released

    # Keep curriculum order from admin overview (_class_entries), not alphabetical.
    results = []
    for row in rows:
        students = row['students_count']
        if students <= 0:
            continue
        class_completed = row['ready_for_you_count'] + row['released_count']
        results.append({
            'display_name': row['display_name'],
            'class_level_id': row['class_level_id'],
            'stream_id': row['stream_id'],
            'students_count': students,
            'pending_count': row['with_class_teacher_count'],
            'ready_count': row['ready_for_you_count'],
            'released_count': row['released_count'],
            'needs_correction_count': row['needs_correction_count'],
            'percent_complete': round(100.0 * class_completed / students, 1) if students else 0.0,
            'percent_released': (
                round(100.0 * row['released_count'] / students, 1) if students else 0.0
            ),
        })

    return {
        'term_id': str(term.id),
        'term_label': _term_label(term),
        'pending_count': pending,
        'ready_count': ready,
        'released_count': released,
        'needs_correction_count': needs_correction,
        'total_students': total_students,
        'percent_complete': round(100.0 * completed / total_students, 1) if total_students else None,
        'percent_released': (
            round(100.0 * released / total_students, 1) if total_students else None
        ),
        'results': results,
    }


def get_fees_academic_risk(*, school, membership, term_id=None, limit=10):
    """Debtors whose academic average is below the pass mark (school-wide)."""
    term = _resolve_term(school=school, term_id=term_id)
    scope = _scope_for_membership(membership)
    if scope.is_scoped:
        return {
            'term_id': str(term.id),
            'term_label': _term_label(term),
            'available': False,
            'debtors_count': 0,
            'at_risk_count': 0,
            'results': [],
        }

    from fees.services.desk import list_fee_desk_rows

    rows, pass_marks = collect_published_scores(school=school, term=term, scope=scope)
    overall = student_overall_averages(rows)
    pass_mark = _dominant_pass_mark(rows, pass_marks)

    fee_rows = list_fee_desk_rows(school=school, term=term)
    debtors = [
        row for row in fee_rows
        if (row.total_billed or 0) > (row.total_paid or 0)
    ]
    class_label_by_student = {}
    for score_row in rows:
        class_label_by_student.setdefault(score_row.student_id, score_row.class_display_name)

    at_risk = []
    for enrollment in debtors:
        average = overall.get(enrollment.student_id)
        if average is None or average >= pass_mark:
            continue
        student = enrollment.student
        outstanding = (enrollment.total_billed or Decimal('0')) - (
            enrollment.total_paid or Decimal('0')
        )
        parts = [student.first_name, getattr(student, 'other_names', None), student.last_name]
        at_risk.append({
            'id': str(student.id),
            'full_name': ' '.join(part for part in parts if part).strip(),
            'student_id': student.student_id,
            'class_display_name': class_label_by_student.get(student.id),
            'average_score': float(average),
            'outstanding_amount': float(outstanding),
        })

    at_risk.sort(key=lambda item: (-item['outstanding_amount'], item['average_score']))
    limit = max(1, min(int(limit or 10), 50))

    return {
        'term_id': str(term.id),
        'term_label': _term_label(term),
        'available': True,
        'pass_mark': float(pass_mark),
        'debtors_count': len(debtors),
        'at_risk_count': len(at_risk),
        'results': at_risk[:limit],
    }


def get_student_trends(
    *,
    school,
    membership,
    term_id=None,
    level_id=None,
    class_level_id=None,
    limit=20,
):
    """Top / at-risk students for the selected term, plus recent-term averages."""
    term = _resolve_term(school=school, term_id=term_id)
    scope = _scope_for_membership(membership)
    rows, pass_marks = collect_published_scores(
        school=school,
        term=term,
        scope=scope,
        class_level_id=class_level_id,
        level_id=level_id,
    )
    students_count = _count_enrolled(
        term=term,
        scope=scope,
        class_level_id=class_level_id,
        level_id=level_id,
    )
    overall = student_overall_averages(rows)
    if not overall:
        return {
            'term_id': str(term.id),
            'term_label': _term_label(term),
            'pass_mark': float(DEFAULT_PASS_MARK),
            'students_count': students_count,
            'students_with_results': 0,
            'below_pass_count': 0,
            'top_students': [],
            'at_risk_students': [],
        }

    pass_mark = _dominant_pass_mark(rows, pass_marks)
    student_ids = list(overall.keys())
    students = {
        student.id: student
        for student in Student.objects.filter(id__in=student_ids).only(
            'id', 'first_name', 'other_names', 'last_name', 'student_id',
        )
    }

    class_label_by_student: dict[UUID, str] = {}
    for row in rows:
        class_label_by_student.setdefault(row.student_id, row.class_display_name)

    def _full_name(student) -> str:
        parts = [student.first_name, getattr(student, 'other_names', None), student.last_name]
        return ' '.join(part for part in parts if part).strip()

    ranked = sorted(overall.items(), key=lambda item: (-item[1], str(item[0])))
    limit = max(1, min(int(limit or 20), 50))

    def _serialize(entries):
        payload = []
        for student_id, average in entries:
            student = students.get(student_id)
            if student is None:
                continue
            payload.append({
                'id': str(student_id),
                'full_name': _full_name(student),
                'student_id': student.student_id,
                'class_display_name': class_label_by_student.get(student_id),
                'average_score': float(average),
                'is_passing': average >= pass_mark,
            })
        return payload

    top_students = _serialize(ranked[:limit])
    below_pass = [(sid, avg) for sid, avg in reversed(ranked) if avg < pass_mark]
    at_risk_students = _serialize(below_pass[:limit])
    # Full count of students below the pass mark (not capped by limit).
    below_pass_count = len(below_pass)

    # Term history for the students shown (up to 4 recent terms)
    shown_ids = {UUID(item['id']) for item in top_students} | {
        UUID(item['id']) for item in at_risk_students
    }
    recent_terms = list(
        Term.objects.filter(school=school, start_date__lte=term.start_date)
        .select_related('academic_year')
        .order_by('-start_date', '-id')[:4]
    )
    history_by_student: dict[str, list] = defaultdict(list)
    for history_term in reversed(recent_terms):
        history_rows, _ = collect_published_scores(
            school=school,
            term=history_term,
            scope=scope,
            class_level_id=class_level_id,
            level_id=level_id,
        )
        history_overall = student_overall_averages(history_rows)
        for student_id in shown_ids:
            if student_id not in history_overall:
                continue
            history_by_student[str(student_id)].append({
                'term_id': str(history_term.id),
                'term_label': _term_label(history_term),
                'average_score': float(history_overall[student_id]),
            })

    for item in top_students:
        item['history'] = history_by_student.get(item['id'], [])
    for item in at_risk_students:
        item['history'] = history_by_student.get(item['id'], [])

    return {
        'term_id': str(term.id),
        'term_label': _term_label(term),
        'pass_mark': float(pass_mark),
        'students_count': students_count,
        'students_with_results': len(overall),
        'below_pass_count': below_pass_count,
        'top_students': top_students,
        'at_risk_students': at_risk_students,
    }


def get_finance(*, school, membership, term_id=None, limit=10):
    """Fee collection health + debtors by class (school-wide)."""
    term = _resolve_term(school=school, term_id=term_id)
    scope = _scope_for_membership(membership)
    if scope.is_scoped:
        return {
            'term_id': str(term.id),
            'term_label': _term_label(term),
            'available': False,
            'total_expected': 0.0,
            'total_collected': 0.0,
            'outstanding': 0.0,
            'collection_rate': None,
            'debtors_count': 0,
            'debtors_by_class': [],
            'top_debtors': [],
        }

    from fees.services.desk import get_fee_desk_stats, list_fee_desk_rows

    fee_qs = list_fee_desk_rows(school=school, term=term)
    stats = get_fee_desk_stats(queryset=fee_qs)
    fee_rows = list(fee_qs)
    expected = float(stats['total_expected'] or 0)
    collected = float(stats['total_collected'] or 0)
    outstanding = float(stats['outstanding'] or 0)
    collection_rate = round(100.0 * collected / expected, 1) if expected > 0 else None

    by_class: dict[str, dict] = {}
    top_debtors = []
    for row in fee_rows:
        billed = Decimal(row.total_billed or 0)
        paid = Decimal(row.total_paid or 0)
        owing = billed - paid
        if owing <= 0:
            continue
        display = row.stream.full_name if row.stream_id else row.class_level.name
        bucket = by_class.setdefault(
            display,
            {'display_name': display, 'debtors_count': 0, 'outstanding': Decimal('0')},
        )
        bucket['debtors_count'] += 1
        bucket['outstanding'] += owing
        student = row.student
        parts = [student.first_name, getattr(student, 'other_names', None), student.last_name]
        top_debtors.append({
            'id': str(student.id),
            'full_name': ' '.join(part for part in parts if part).strip(),
            'student_id': student.student_id,
            'class_display_name': display,
            'outstanding_amount': float(owing),
        })

    top_debtors.sort(key=lambda item: -item['outstanding_amount'])
    debtors_by_class = sorted(
        (
            {
                'display_name': item['display_name'],
                'debtors_count': item['debtors_count'],
                'outstanding_amount': float(item['outstanding']),
            }
            for item in by_class.values()
        ),
        key=lambda item: -item['outstanding_amount'],
    )
    limit = max(1, min(int(limit or 10), 50))

    return {
        'term_id': str(term.id),
        'term_label': _term_label(term),
        'available': True,
        'total_expected': expected,
        'total_collected': collected,
        'outstanding': outstanding,
        'collection_rate': collection_rate,
        'debtors_count': stats['debtors_count'] or 0,
        'debtors_by_class': debtors_by_class,
        'top_debtors': top_debtors[:limit],
    }


def get_enrollment(*, school, membership, term_id=None):
    """Retention-style enrollment change vs previous term."""
    from students.models import ClassEnrollment

    term = _resolve_term(school=school, term_id=term_id)
    scope = _scope_for_membership(membership)
    previous = (
        Term.objects.filter(school=school, start_date__lt=term.start_date)
        .order_by('-start_date', '-id')
        .first()
    )

    current_qs = ClassEnrollment.objects.filter(term=term).select_related(
        'student',
        'stream',
        'class_level',
    )
    if scope.is_scoped and scope.visible_stream_ids:
        current_qs = current_qs.filter(stream_id__in=scope.visible_stream_ids)

    current_rows = list(current_qs)
    current_ids = {row.student_id for row in current_rows}
    new_count = sum(1 for row in current_rows if row.is_new_student)

    previous_ids: set = set()
    if previous is not None:
        prev_qs = ClassEnrollment.objects.filter(term=previous)
        if scope.is_scoped and scope.visible_stream_ids:
            prev_qs = prev_qs.filter(stream_id__in=scope.visible_stream_ids)
        previous_ids = set(prev_qs.values_list('student_id', flat=True))

    retained = len(current_ids & previous_ids) if previous else None

    graduated_count = None
    left_count = None
    left_by_reason: Counter = Counter()
    if previous is not None:
        missing = previous_ids - current_ids
        graduated_ids = set(
            Student.objects.filter(id__in=missing, is_graduated=True).values_list(
                'id',
                flat=True,
            )
        )
        left_rows = list(
            Student.objects.filter(
                id__in=missing,
                is_active=False,
                left_at__isnull=False,
                is_graduated=False,
            ).only('id', 'leave_reason')
        )
        for row in left_rows:
            left_by_reason[row.leave_reason or 'other'] += 1
        graduated_count = len(graduated_ids)
        left_count = len(left_rows)

    by_class = []
    class_counts: dict[str, int] = defaultdict(int)
    for row in current_rows:
        label = row.stream.full_name if row.stream_id else row.class_level.name
        class_counts[label] += 1
    for label, count in sorted(class_counts.items(), key=lambda item: item[0].lower()):
        by_class.append({'display_name': label, 'students_count': count})

    retention_rate = None
    if previous is not None and previous_ids:
        # Retained among non-graduated previous cohort
        prev_non_grad = previous_ids - set(
            Student.objects.filter(id__in=previous_ids, is_graduated=True).values_list(
                'id',
                flat=True,
            )
        )
        if prev_non_grad:
            retention_rate = round(
                100.0 * len(current_ids & prev_non_grad) / len(prev_non_grad),
                1,
            )

    return {
        'term_id': str(term.id),
        'term_label': _term_label(term),
        'previous_term_id': str(previous.id) if previous else None,
        'previous_term_label': _term_label(previous) if previous else None,
        'enrolled_count': len(current_ids),
        'new_students': new_count,
        'retained_count': retained,
        'graduated_count': graduated_count if previous else None,
        'left_count': left_count if previous else None,
        'left_by_reason': [
            {'reason': reason, 'count': count}
            for reason, count in left_by_reason.items()
        ],
        'retention_rate': retention_rate,
        'by_class': by_class,
    }


def get_staff_capacity(*, school, membership, term_id=None):
    """Per-teacher load insights for the term (class teacher + subject teaching)."""
    from teachers.models import ClassTeacher, TeachingAssignment

    term = _resolve_term(school=school, term_id=term_id)
    scope = _scope_for_membership(membership)
    sizes = _enrollment_size_maps(term=term, scope=scope)
    size_by_key = sizes['by_key']

    teachers: dict = {}

    def _ensure_teacher(user) -> dict:
        teacher_id = user.id
        row = teachers.get(teacher_id)
        if row is not None:
            return row
        name = (user.get_full_name() or '').strip() or user.email or 'Teacher'
        row = {
            'teacher_id': str(teacher_id),
            'full_name': name,
            'class_teacher_classes': [],
            'class_teacher_students': 0,
            'subject_names': set(),
            'teaching_class_names': set(),
            'assignments': [],
            'teaching_assignments_count': 0,
        }
        teachers[teacher_id] = row
        return row

    def _students_for_class_teacher(*, class_level_id, stream_id) -> int:
        if stream_id is not None:
            return size_by_key.get((class_level_id, stream_id), 0)
        return sum(
            count
            for (level_id, _stream_id), count in size_by_key.items()
            if level_id == class_level_id
        )

    covered_keys: set[tuple] = set()
    class_teacher_qs = ClassTeacher.objects.filter(term=term).select_related(
        'teacher',
        'class_level',
        'stream',
    )
    for assignment in class_teacher_qs:
        if (
            scope.is_scoped
            and scope.visible_stream_ids
            and assignment.stream_id
            and assignment.stream_id not in scope.visible_stream_ids
        ):
            continue
        row = _ensure_teacher(assignment.teacher)
        if assignment.stream_id:
            label = assignment.stream.full_name
            covered_keys.add((assignment.class_level_id, assignment.stream_id))
        else:
            label = assignment.class_level.name
            for key in size_by_key:
                if key[0] == assignment.class_level_id:
                    covered_keys.add(key)
        row['class_teacher_classes'].append(label)
        row['class_teacher_students'] += _students_for_class_teacher(
            class_level_id=assignment.class_level_id,
            stream_id=assignment.stream_id,
        )

    teaching_qs = TeachingAssignment.objects.filter(term=term).select_related(
        'teacher',
        'class_subject',
        'class_subject__subject',
        'class_subject__class_level',
        'stream',
    )
    for assignment in teaching_qs:
        if (
            scope.is_scoped
            and scope.visible_stream_ids
            and assignment.stream_id
            and assignment.stream_id not in scope.visible_stream_ids
        ):
            continue
        row = _ensure_teacher(assignment.teacher)
        subject_name = assignment.class_subject.subject.name
        class_label = (
            assignment.stream.full_name
            if assignment.stream_id
            else assignment.class_subject.class_level.name
        )
        row['subject_names'].add(subject_name)
        row['teaching_class_names'].add(class_label)
        row['assignments'].append(f'{subject_name} · {class_label}')
        row['teaching_assignments_count'] += 1

    results = []
    for row in teachers.values():
        class_teacher_classes = sorted(row['class_teacher_classes'])
        subject_names = sorted(row['subject_names'])
        teaching_classes = sorted(row['teaching_class_names'])
        assignments = sorted(row['assignments'])
        class_teacher_count = len(class_teacher_classes)
        teaching_assignments_count = row['teaching_assignments_count']
        results.append({
            'teacher_id': row['teacher_id'],
            'full_name': row['full_name'],
            'is_class_teacher': class_teacher_count > 0,
            'is_subject_teacher': teaching_assignments_count > 0,
            'class_teacher_count': class_teacher_count,
            'class_teacher_classes': class_teacher_classes,
            'class_teacher_students': row['class_teacher_students'],
            'subjects_taught_count': len(subject_names),
            'subject_names': subject_names,
            'teaching_assignments_count': teaching_assignments_count,
            'classes_taught_count': len(teaching_classes),
            'teaching_classes': teaching_classes,
            'assignments': assignments,
        })

    results.sort(
        key=lambda item: (
            -(item['teaching_assignments_count'] + item['class_teacher_count']),
            -item['teaching_assignments_count'],
            item['full_name'].lower(),
        )
    )

    teachers_count = len(results)
    class_teachers_count = sum(1 for item in results if item['is_class_teacher'])
    subject_teachers_count = sum(1 for item in results if item['is_subject_teacher'])
    both_roles_count = sum(
        1 for item in results if item['is_class_teacher'] and item['is_subject_teacher']
    )
    classes_count = len(size_by_key)
    classes_without_class_teacher = sum(
        1 for key in size_by_key if key not in covered_keys
    )
    total_assignments = sum(item['teaching_assignments_count'] for item in results)
    average_assignments = (
        round(total_assignments / teachers_count, 1) if teachers_count else None
    )

    return {
        'term_id': str(term.id),
        'term_label': _term_label(term),
        'teachers_count': teachers_count,
        'class_teachers_count': class_teachers_count,
        'subject_teachers_count': subject_teachers_count,
        'both_roles_count': both_roles_count,
        'classes_count': classes_count,
        'classes_without_class_teacher': classes_without_class_teacher,
        'average_assignments': average_assignments,
        'results': results,
    }


def _grade_distribution_payload(grades: list[str], band_order: list[str]) -> dict:
    counts: Counter = Counter(grade for grade in grades if grade)
    graded = sum(counts.values())
    order = band_order or sorted(counts.keys())
    results = []
    for grade in order:
        count = counts.get(grade, 0)
        results.append({
            'grade': grade,
            'count': count,
            'percent': round(100.0 * count / graded, 1) if graded else 0.0,
        })
    for grade, count in counts.items():
        if grade in order:
            continue
        results.append({
            'grade': grade,
            'count': count,
            'percent': round(100.0 * count / graded, 1) if graded else 0.0,
        })
    return {'total_graded': graded, 'results': results}


def _config_for_level(*, term, level_id):
    return (
        AssessmentConfig.objects.filter(term_id=term.id, level_id=level_id)
        .prefetch_related('grade_bands')
        .first()
    )


def _bands_for_level(*, term, level_id):
    config = _config_for_level(term=term, level_id=level_id)
    if config is None:
        return []
    return list(config.grade_bands.all())


def _desk_distribution(*, config, pass_mark, grade_labels=None, score_values=None) -> dict:
    """
    Grade pie payload for teacher desk.

    Grade / grade+position → letter/number bands.
    Position-only → score ranges (same shape as admin Academics).
    """
    uses_grades = config.uses_grades() if config is not None else True
    result_type = (
        config.result_type
        if config is not None
        else AssessmentConfig.ResultType.GRADE_AND_POSITION
    )
    if uses_grades:
        bands = list(config.grade_bands.all()) if config is not None else []
        band_order = [band.grade for band in bands]
        payload = _grade_distribution_payload(grade_labels or [], band_order)
        return {
            'mode': 'grades',
            'result_type': result_type,
            'total_graded': payload['total_graded'],
            'grade_distribution': payload['results'],
        }

    bands = _score_band_specs(pass_mark)
    band_order = [label for _low, _high, label in bands]
    counts: Counter = Counter(
        _bucket_total(value, bands) for value in (score_values or [])
    )
    total = sum(counts.values())
    return {
        'mode': 'score_bands',
        'result_type': result_type,
        'total_graded': total,
        'grade_distribution': _distribution_results(counts, band_order, total),
    }


def _student_full_name(student) -> str:
    parts = [student.first_name, getattr(student, 'other_names', None), student.last_name]
    return ' '.join(part for part in parts if part).strip()


def _recent_terms(*, school, term):
    recent = list(
        Term.objects.filter(school=school, start_date__lte=term.start_date)
        .select_related('academic_year')
        .order_by('-start_date', '-id')[:4]
    )
    return list(reversed(recent))


def build_class_performance(
    *,
    school,
    term,
    class_level,
    stream_id=None,
    display_name=None,
    collect_scope=None,
):
    """Class-perspective performance payload for one stream (or whole class level)."""
    from assessments.services.scoring import resolve_grade

    rows, pass_marks = collect_published_scores(
        school=school,
        term=term,
        scope=collect_scope,
        class_level_id=class_level.id,
    )
    if stream_id:
        rows = [row for row in rows if row.stream_id == stream_id]

    overall = student_overall_averages(rows)
    overall_values = list(overall.values())
    pass_mark = pass_marks.get(class_level.level_id, DEFAULT_PASS_MARK)
    config = _config_for_level(term=term, level_id=class_level.level_id)
    bands = list(config.grade_bands.all()) if config is not None else []
    overall_grades = []
    for average in overall_values:
        grade = resolve_grade(average, bands) if bands else None
        if grade:
            overall_grades.append(grade)
    distribution = _desk_distribution(
        config=config,
        pass_mark=pass_mark,
        grade_labels=overall_grades,
        score_values=overall_values,
    )

    student_ids = list(overall.keys())
    students_by_id = {
        student.id: student
        for student in Student.objects.filter(id__in=student_ids).only(
            'id', 'first_name', 'other_names', 'last_name', 'student_id',
        )
    }
    ranked = sorted(overall.items(), key=lambda item: (-item[1], str(item[0])))
    student_rows = []
    for student_id, average in ranked:
        student = students_by_id.get(student_id)
        if student is None:
            continue
        grade = resolve_grade(average, bands) if bands else None
        student_rows.append({
            'id': str(student_id),
            'full_name': _student_full_name(student),
            'student_id': student.student_id,
            'average_score': float(average),
            'grade': grade,
            'is_passing': average >= pass_mark,
        })

    resolved_name = display_name
    if not resolved_name:
        if stream_id:
            stream = ClassStream.objects.filter(id=stream_id).first()
            resolved_name = stream.full_name if stream is not None else class_level.name
        else:
            resolved_name = class_level.name

    students_count = _count_enrolled(
        term=term,
        class_level_id=class_level.id,
        stream_id=stream_id,
    )
    return {
        'class_level_id': str(class_level.id),
        'stream_id': str(stream_id) if stream_id else None,
        'display_name': resolved_name,
        'level_id': str(class_level.level_id),
        'students_count': students_count,
        'students_with_results': len(overall_values),
        'average_score': average_or_none(overall_values),
        'pass_rate': pass_rate(overall_values, pass_mark),
        'pass_mark': float(pass_mark),
        'mode': distribution['mode'],
        'result_type': distribution['result_type'],
        'total_graded': distribution['total_graded'],
        'grade_distribution': distribution['grade_distribution'],
        'students': student_rows,
    }


def build_subject_performance(
    *,
    school,
    term,
    assignment,
    collect_scope=None,
    history_teacher_id=None,
):
    """Subject-perspective performance for one teaching assignment."""
    from teachers.models import TeachingAssignment

    class_subject = assignment.class_subject
    class_level = class_subject.class_level
    rows, pass_marks = collect_published_scores(
        school=school,
        term=term,
        scope=collect_scope,
        class_level_id=class_level.id,
    )
    rows = [row for row in rows if row.teaching_assignment_id == assignment.id]
    totals = [row.total for row in rows]
    pass_mark = pass_marks.get(class_level.level_id, DEFAULT_PASS_MARK)
    config = _config_for_level(term=term, level_id=class_level.level_id)
    distribution = _desk_distribution(
        config=config,
        pass_mark=pass_mark,
        grade_labels=[row.grade for row in rows if row.grade],
        score_values=totals,
    )

    student_ids = {row.student_id for row in rows}
    students_by_id = {
        student.id: student
        for student in Student.objects.filter(id__in=student_ids).only(
            'id', 'first_name', 'other_names', 'last_name', 'student_id',
        )
    }
    student_rows = []
    for row in sorted(rows, key=lambda item: (-item.total, item.subject_name)):
        student = students_by_id.get(row.student_id)
        if student is None:
            continue
        student_rows.append({
            'id': str(row.student_id),
            'full_name': _student_full_name(student),
            'student_id': student.student_id,
            'average_score': float(row.total),
            'grade': row.grade,
            'is_passing': row.total >= pass_mark,
        })

    term_history = []
    for history_term in _recent_terms(school=school, term=term):
        history_qs = TeachingAssignment.objects.filter(
            term=history_term,
            class_subject_id=class_subject.id,
            stream_id=assignment.stream_id,
        )
        if history_teacher_id is not None:
            history_qs = history_qs.filter(teacher_id=history_teacher_id)
        if assignment.subject_group_id:
            history_qs = history_qs.filter(subject_group_id=assignment.subject_group_id)
        history_assignment = history_qs.only('id').first()
        if history_assignment is None:
            continue
        history_rows, _ = collect_published_scores(
            school=school,
            term=history_term,
            scope=collect_scope,
            class_level_id=class_level.id,
        )
        history_totals = [
            row.total
            for row in history_rows
            if row.teaching_assignment_id == history_assignment.id
        ]
        if not history_totals:
            continue
        term_history.append({
            'term_id': str(history_term.id),
            'term_label': _term_label(history_term),
            'average_score': average_or_none(history_totals),
        })

    stream_label = (
        assignment.stream.full_name
        if assignment.stream_id
        else class_level.name
    )
    students_count = _count_enrolled(
        term=term,
        class_level_id=class_level.id,
        stream_id=assignment.stream_id,
    )
    return {
        'teaching_assignment_id': str(assignment.id),
        'subject_id': str(class_subject.subject_id),
        'subject_name': class_subject.subject.name,
        'class_level_id': str(class_level.id),
        'stream_id': str(assignment.stream_id) if assignment.stream_id else None,
        'display_name': f'{class_subject.subject.name} · {stream_label}',
        'students_count': students_count,
        'score_count': len(totals),
        'average_score': average_or_none(totals),
        'pass_rate': pass_rate(totals, pass_mark),
        'pass_mark': float(pass_mark),
        'mode': distribution['mode'],
        'result_type': distribution['result_type'],
        'total_graded': distribution['total_graded'],
        'grade_distribution': distribution['grade_distribution'],
        'term_history': term_history,
        'students': student_rows,
    }


def get_class_stream_performance(*, school, membership, stream_id, term_id=None) -> dict:
    """Full class performance for a stream (admin or anyone who can view the class)."""
    from academics.services.class_detail import get_stream_for_school
    from rest_framework.exceptions import PermissionDenied

    term = _resolve_term(school=school, term_id=term_id)
    stream = get_stream_for_school(school=school, stream_id=stream_id)
    scope = _scope_for_membership(membership)
    if scope.is_scoped and scope.visible_stream_ids and stream.id not in scope.visible_stream_ids:
        raise PermissionDenied('You can only view performance for your classes.')

    payload = build_class_performance(
        school=school,
        term=term,
        class_level=stream.class_level,
        stream_id=stream.id,
        display_name=stream.full_name,
        collect_scope=None,
    )
    return {
        'term_id': str(term.id),
        'term_label': _term_label(term),
        **payload,
    }


def get_teaching_assignment_performance(
    *,
    school,
    membership,
    teaching_assignment_id,
    term_id=None,
) -> dict:
    """Subject performance for one teaching assignment."""
    from academics.services.teaching_assignments import (
        ensure_can_view_teaching_assignment,
        get_teaching_assignment,
    )

    del term_id  # Assignment is already tied to a term.
    assignment = get_teaching_assignment(
        school=school,
        assignment_id=teaching_assignment_id,
    )
    ensure_can_view_teaching_assignment(membership, assignment)
    term = assignment.term

    payload = build_subject_performance(
        school=school,
        term=term,
        assignment=assignment,
        collect_scope=None,
        history_teacher_id=None,
    )
    return {
        'term_id': str(term.id),
        'term_label': _term_label(term),
        **payload,
    }


def get_teacher_desk(*, school, membership, term_id=None) -> dict:
    """Class/subject teacher performance desk for the selected term."""
    from teachers.models import ClassTeacher, TeachingAssignment

    term = _resolve_term(school=school, term_id=term_id)
    scope = _scope_for_membership(membership)

    empty = {
        'term_id': str(term.id),
        'term_label': _term_label(term),
        'scope_mode': scope.mode,
        'is_class_teacher': scope.is_class_teacher,
        'is_subject_teacher': scope.is_subject_teacher,
        'classes': [],
        'subjects': [],
    }
    if not scope.is_scoped:
        return empty

    classes = []
    if scope.is_class_teacher:
        class_teacher_rows = list(
            ClassTeacher.objects.filter(teacher_id=membership.user_id, term=term)
            .select_related('class_level', 'class_level__level', 'stream')
            .order_by('class_level__level__order', 'class_level__order', 'class_level__name')
        )
        for class_teacher in class_teacher_rows:
            display_name = (
                class_teacher.stream.full_name
                if class_teacher.stream_id
                else class_teacher.class_level.name
            )
            classes.append(
                build_class_performance(
                    school=school,
                    term=term,
                    class_level=class_teacher.class_level,
                    stream_id=class_teacher.stream_id,
                    display_name=display_name,
                    collect_scope=scope,
                )
            )

    subjects = []
    if scope.is_subject_teacher:
        assignments = list(
            TeachingAssignment.objects.filter(teacher_id=membership.user_id, term=term)
            .select_related(
                'class_subject',
                'class_subject__subject',
                'class_subject__class_level',
                'class_subject__class_level__level',
                'stream',
            )
            .order_by(
                'class_subject__class_level__level__order',
                'class_subject__class_level__order',
                'class_subject__subject__name',
            )
        )
        for assignment in assignments:
            subjects.append(
                build_subject_performance(
                    school=school,
                    term=term,
                    assignment=assignment,
                    collect_scope=scope,
                    history_teacher_id=membership.user_id,
                )
            )

    return {
        'term_id': str(term.id),
        'term_label': _term_label(term),
        'scope_mode': scope.mode,
        'is_class_teacher': scope.is_class_teacher,
        'is_subject_teacher': scope.is_subject_teacher,
        'classes': classes,
        'subjects': subjects,
    }


def _rate_subject_score(score: Decimal | float, pass_mark: Decimal) -> str:
    value = Decimal(str(score))
    if value >= pass_mark + Decimal('20'):
        return 'strong'
    if value >= pass_mark:
        return 'secure'
    if value >= pass_mark - Decimal('10'):
        return 'borderline'
    return 'at_risk'


def _ranked_subjects(rows, *, pass_mark: Decimal) -> list[dict]:
    ordered = sorted(rows, key=lambda item: (-item.total, item.subject_name.lower()))
    ranked = []
    for index, row in enumerate(ordered, start=1):
        ranked.append({
            'rank': index,
            'subject_id': str(row.subject_id),
            'subject_name': row.subject_name,
            'total': float(row.total),
            'grade': row.grade,
            'rating': _rate_subject_score(row.total, pass_mark),
        })
    return ranked


def get_student_performance(*, school, student_id) -> dict:
    """Subject scores and averages across enrolled terms for one student."""
    from academics.models import ClassSubject
    from students.models import ClassEnrollment
    from students.services import get_student

    student = get_student(school=school, student_id=student_id)
    enrollments = list(
        ClassEnrollment.objects.filter(student=student)
        .select_related('term__academic_year', 'stream', 'class_level')
        .order_by('term__start_date', 'term__created_at')
    )

    terms_payload = []
    subject_points: dict[str, list] = defaultdict(list)
    enrolled_term_count = len(enrollments)

    for enrollment in enrollments:
        term = enrollment.term
        rows, pass_marks = collect_published_scores(school=school, term=term, scope=None)
        student_rows = [row for row in rows if row.student_id == student.id]
        overall = student_overall_averages(student_rows)
        average = overall.get(student.id)

        level_id = enrollment.class_level.level_id
        pass_mark = pass_marks.get(level_id, DEFAULT_PASS_MARK)
        config = _config_for_level(term=term, level_id=level_id)
        distribution = _desk_distribution(
            config=config,
            pass_mark=pass_mark,
            grade_labels=[row.grade for row in student_rows if row.grade],
            score_values=[row.total for row in student_rows],
        )
        ranked = _ranked_subjects(student_rows, pass_mark=pass_mark)

        for row in student_rows:
            subject_points[row.subject_name].append({
                'term_id': str(term.id),
                'term_label': _term_label(term),
                'total': float(row.total),
            })

        expected_subjects = ClassSubject.objects.filter(
            class_level_id=enrollment.class_level_id,
            is_active=True,
        ).count()
        published_count = len(student_rows)
        missing_count = max(expected_subjects - published_count, 0)

        terms_payload.append({
            'term_id': str(term.id),
            'term_label': _term_label(term),
            'class_display_name': (
                enrollment.stream.full_name
                if enrollment.stream_id
                else enrollment.class_level.name
            ),
            'overall_average': float(average) if average is not None else None,
            'pass_mark': float(pass_mark),
            'mode': distribution['mode'],
            'result_type': distribution['result_type'],
            'subjects': ranked,
            'total_graded': distribution['total_graded'],
            'grade_distribution': distribution['grade_distribution'],
            'expected_subjects_count': expected_subjects,
            'published_subjects_count': published_count,
            'missing_subjects_count': missing_count,
            'results_incomplete': missing_count > 0,
        })

    # All-time: average each subject across terms that have a published score.
    latest_pass_mark = (
        Decimal(str(terms_payload[-1]['pass_mark']))
        if terms_payload
        else DEFAULT_PASS_MARK
    )
    all_time_rows = []
    for subject_name, points in subject_points.items():
        totals = [Decimal(str(point['total'])) for point in points]
        average = sum(totals) / Decimal(len(totals))
        terms_with_score = len(points)
        all_time_rows.append({
            'subject_name': subject_name,
            'total': float(average.quantize(Decimal('0.01'))),
            'grade': None,
            'terms_with_score': terms_with_score,
            'terms_enrolled': enrolled_term_count,
            'incomplete': (
                enrolled_term_count > 0 and terms_with_score < enrolled_term_count
            ),
            'rating': _rate_subject_score(average, latest_pass_mark),
        })
    all_time_rows.sort(key=lambda item: (-item['total'], item['subject_name'].lower()))
    all_time_ranking = []
    for index, row in enumerate(all_time_rows, start=1):
        all_time_ranking.append({
            'rank': index,
            'subject_id': None,
            'subject_name': row['subject_name'],
            'total': row['total'],
            'grade': row['grade'],
            'rating': row['rating'],
            'terms_with_score': row['terms_with_score'],
            'terms_enrolled': row['terms_enrolled'],
            'incomplete': row['incomplete'],
        })

    subject_trends = [
        {
            'subject_name': subject_name,
            'points': points,
        }
        for subject_name, points in sorted(subject_points.items(), key=lambda item: item[0].lower())
    ]
    overall_trend = [
        {
            'term_id': item['term_id'],
            'term_label': item['term_label'],
            'average_score': item['overall_average'],
        }
        for item in terms_payload
        if item['overall_average'] is not None
    ]

    return {
        'student_id': str(student.id),
        'full_name': _student_full_name(student),
        'terms': terms_payload,
        'overall_trend': overall_trend,
        'subject_trends': subject_trends,
        'all_time_ranking': all_time_ranking,
        'all_time_pass_mark': float(latest_pass_mark),
        'all_time_incomplete': any(row['incomplete'] for row in all_time_ranking),
        'enrolled_term_count': enrolled_term_count,
    }
