"""School-wide admin dashboard aggregations for the active term."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Value
from django.db.models.functions import Coalesce

from academics.models import ClassLevel
from academics.services.classes import get_class_stats
from accounts.models import SchoolMembership
from assessments.services.admin_overview import list_admin_assessment_overview
from fees.services.desk import get_fee_desk_stats, list_fee_desk_rows
from schools.models import Term
from students.services import get_student_stats


TOP_DEBTORS_LIMIT = 5


def get_admin_dashboard(*, school) -> dict:
    """Aggregate actionable school overview data for admins."""
    term = (
        Term.objects.filter(school=school, is_active=True)
        .select_related('academic_year')
        .first()
    )
    if term is None:
        return _empty_dashboard(school=school)

    class_stats = get_class_stats(school=school, term=term)
    student_stats = get_student_stats(school=school, term=term)
    fee_rows = list_fee_desk_rows(school=school, term=term)
    fee_stats = get_fee_desk_stats(queryset=fee_rows)
    assessment = list_admin_assessment_overview(school=school, term_id=term.id)
    staff_count = SchoolMembership.objects.filter(school=school, is_active=True).count()

    ready = assessment['ready_for_you_count']
    pending = assessment['with_class_teacher_count']
    released = assessment['released_count']
    needs_correction = assessment['needs_correction_count']
    inbox_count = assessment['corrections_inbox_count']

    show_academic_widgets = any(
        (
            ready > 0,
            released > 0,
            needs_correction > 0,
            inbox_count > 0,
        )
    )

    needs_attention = _build_needs_attention(
        ready_for_you=ready,
        unassigned_classes=class_stats['unassigned_classes'],
        debtors_count=fee_stats['debtors_count'],
        unassigned_subjects=class_stats['unassigned_class_subjects'],
        corrections_inbox=inbox_count,
        empty_classes=class_stats['empty_classes'],
        needs_correction=needs_correction,
    )

    return {
        'term_id': str(term.id),
        'term_label': f'{term.academic_year.academic_year} · {term.get_term_display()}',
        'show_academic_widgets': show_academic_widgets,
        'school_overview': {
            'total_students': student_stats['total_students'],
            'total_classes': class_stats['total_classes'],
            'staff_members': staff_count,
        },
        'fees_overview': {
            'fees_collected': fee_stats['total_collected'],
            'outstanding_balance': fee_stats['outstanding'],
            'debtors_count': fee_stats['debtors_count'],
        },
        'academic_overview': {
            'reports_ready': ready,
            'pending_reports': pending,
            'released_reports': released,
            'needs_correction': needs_correction,
        },
        'coverage_overview': {
            'unassigned_classes': class_stats['unassigned_classes'],
            'unassigned_subjects': class_stats['unassigned_class_subjects'],
            'empty_classes': class_stats['empty_classes'],
        },
        'needs_attention': needs_attention,
        'top_debtors': _top_debtors(fee_rows),
        'setup_health': _setup_health(school=school, term=term, class_stats=class_stats),
        'academic_progress': _academic_progress(school=school, assessment=assessment),
        'levels': _levels_for_progress(school=school, assessment=assessment),
    }


def _empty_dashboard(*, school) -> dict:
    staff_count = SchoolMembership.objects.filter(school=school, is_active=True).count()
    return {
        'term_id': None,
        'term_label': None,
        'show_academic_widgets': False,
        'school_overview': {
            'total_students': 0,
            'total_classes': 0,
            'staff_members': staff_count,
        },
        'fees_overview': {
            'fees_collected': Decimal('0.00'),
            'outstanding_balance': Decimal('0.00'),
            'debtors_count': 0,
        },
        'academic_overview': {
            'reports_ready': 0,
            'pending_reports': 0,
            'released_reports': 0,
            'needs_correction': 0,
        },
        'coverage_overview': {
            'unassigned_classes': 0,
            'unassigned_subjects': 0,
            'empty_classes': 0,
        },
        'needs_attention': [],
        'top_debtors': [],
        'setup_health': {
            'class_teachers': {
                'label': 'Classes with a class teacher',
                'assigned': 0,
                'total': 0,
                'percent': 100,
                'href': '/classes?tab=classes',
            },
            'subject_teachers': {
                'label': 'Subjects with a subject teacher',
                'assigned': 0,
                'total': 0,
                'percent': 100,
                'href': '/classes?tab=subjects',
            },
            'classes_with_students': {
                'label': 'Classes with students',
                'assigned': 0,
                'total': 0,
                'percent': 100,
                'href': '/classes?tab=classes',
            },
            'subject_groups_with_students': {
                'label': 'Subject groups with students',
                'assigned': 0,
                'total': 0,
                'percent': 100,
                'href': '/classes?tab=subjects&attention=empty',
            },
            'students_in_subject_groups': {
                'label': 'Students placed in subject groups',
                'assigned': 0,
                'total': 0,
                'percent': 100,
                'href': '/classes?tab=subjects',
            },
        },
        'academic_progress': [],
        'levels': [],
    }


def _build_needs_attention(
    *,
    ready_for_you,
    unassigned_classes,
    debtors_count,
    unassigned_subjects,
    corrections_inbox,
    empty_classes,
    needs_correction,
) -> list[dict]:
    items = []

    if ready_for_you:
        label = (
            f'{ready_for_you} student{"s" if ready_for_you != 1 else ""} '
            f'need{"s" if ready_for_you == 1 else ""} report review'
        )
        items.append({
            'code': 'reports_ready',
            'label': label,
            'count': ready_for_you,
            'href': '/assessments?status=ready_for_you',
        })

    if corrections_inbox:
        label = (
            f'{corrections_inbox} reopen request{"s" if corrections_inbox != 1 else ""} '
            f'awaiting review'
        )
        items.append({
            'code': 'reopen_requests',
            'label': label,
            'count': corrections_inbox,
            'href': '/assessments?inbox=1',
        })

    if needs_correction:
        label = (
            f'{needs_correction} student{"s" if needs_correction != 1 else ""} '
            f'need{"s" if needs_correction == 1 else ""} assessment correction'
        )
        items.append({
            'code': 'needs_correction',
            'label': label,
            'count': needs_correction,
            'href': '/assessments',
        })

    if unassigned_classes:
        label = (
            f'{unassigned_classes} class{"es" if unassigned_classes != 1 else ""} '
            f'ha{"ve" if unassigned_classes != 1 else "s"} no class teacher'
        )
        items.append({
            'code': 'unassigned_classes',
            'label': label,
            'count': unassigned_classes,
            'href': '/classes?tab=classes&attention=unassigned',
        })

    if unassigned_subjects:
        label = (
            f'{unassigned_subjects} subject{"s" if unassigned_subjects != 1 else ""} '
            f'ha{"ve" if unassigned_subjects != 1 else "s"} no subject teacher'
        )
        items.append({
            'code': 'unassigned_subjects',
            'label': label,
            'count': unassigned_subjects,
            'href': '/classes?tab=subjects&attention=unassigned',
        })

    if debtors_count:
        label = (
            f'{debtors_count} student{"s" if debtors_count != 1 else ""} '
            f'owe{"s" if debtors_count == 1 else ""} fees'
        )
        items.append({
            'code': 'debtors',
            'label': label,
            'count': debtors_count,
            'href': '/fees?debtors=true',
        })

    if empty_classes:
        label = (
            f'{empty_classes} class{"es" if empty_classes != 1 else ""} '
            f'ha{"ve" if empty_classes != 1 else "s"} no students'
        )
        items.append({
            'code': 'empty_classes',
            'label': label,
            'count': empty_classes,
            'href': '/classes?tab=classes&attention=empty',
        })

    return items


def _top_debtors(fee_rows) -> list[dict]:
    decimal_field = DecimalField(max_digits=12, decimal_places=2)
    remaining = ExpressionWrapper(
        F('total_billed') - F('total_paid'),
        output_field=decimal_field,
    )
    debtors = (
        fee_rows.filter(total_billed__gt=F('total_paid'))
        .annotate(
            outstanding_amount=Coalesce(
                remaining,
                Value(Decimal('0.00')),
                output_field=decimal_field,
            ),
        )
        .order_by('-outstanding_amount')[:TOP_DEBTORS_LIMIT]
    )

    rows = []
    for enrollment in debtors:
        student = enrollment.student
        full_name = ' '.join(
            part
            for part in (
                student.first_name,
                student.other_names,
                student.last_name,
            )
            if part
        ).strip()
        stream = enrollment.stream
        class_display = stream.full_name if stream is not None else enrollment.class_level.name
        rows.append({
            'student_id': str(student.id),
            'student_code': student.student_id,
            'full_name': full_name,
            'class_display': class_display,
            'outstanding_amount': enrollment.outstanding_amount,
        })
    return rows


def _percent(part: int, whole: int) -> int:
    if whole <= 0:
        return 0
    return round((part / whole) * 100)


def _health_percent(part: int, whole: int) -> int:
    """Setup coverage: nothing to cover counts as complete."""
    if whole <= 0:
        return 100
    return round((part / whole) * 100)


def _health_metric(*, label: str, assigned: int, total: int, href: str) -> dict:
    return {
        'label': label,
        'assigned': assigned,
        'total': total,
        'percent': _health_percent(assigned, total),
        'href': href,
    }


def _subject_group_health(*, school, term) -> dict:
    """Placement coverage for optional subject groups (year-scoped memberships)."""
    from academics.models import StudentSubjectGroup, SubjectGroup
    from students.models import ClassEnrollment

    year = term.academic_year
    groups = list(
        SubjectGroup.objects.filter(
            class_subject__school=school,
            class_subject__is_active=True,
            is_active=True,
        ).values_list('id', 'class_subject_id', 'class_subject__class_level_id')
    )

    if not groups:
        return {
            'subject_groups_with_students': _health_metric(
                label='Subject groups with students',
                assigned=0,
                total=0,
                href='/classes?tab=subjects&attention=empty',
            ),
            'students_in_subject_groups': _health_metric(
                label='Students placed in subject groups',
                assigned=0,
                total=0,
                href='/classes?tab=subjects',
            ),
        }

    group_ids = [group_id for group_id, _, _ in groups]
    class_subjects_by_level: dict = {}
    for _, class_subject_id, class_level_id in groups:
        class_subjects_by_level.setdefault(class_level_id, set()).add(class_subject_id)

    enrollments = list(
        ClassEnrollment.objects.filter(term=term, student__school=school).values_list(
            'student_id',
            'class_level_id',
        )
    )
    enrolled_student_ids = {student_id for student_id, _ in enrollments}

    memberships = list(
        StudentSubjectGroup.objects.filter(
            academic_year=year,
            subject_group_id__in=group_ids,
            student_id__in=enrolled_student_ids,
        ).values_list('student_id', 'class_subject_id', 'subject_group_id')
        if enrolled_student_ids
        else []
    )

    groups_with_students = {subject_group_id for _, _, subject_group_id in memberships}
    placed_pairs = {(student_id, class_subject_id) for student_id, class_subject_id, _ in memberships}

    required = 0
    placed = 0
    for student_id, class_level_id in enrollments:
        for class_subject_id in class_subjects_by_level.get(class_level_id, ()):
            required += 1
            if (student_id, class_subject_id) in placed_pairs:
                placed += 1

    return {
        'subject_groups_with_students': _health_metric(
            label='Subject groups with students',
            assigned=len(groups_with_students),
            total=len(group_ids),
            href='/classes?tab=subjects&attention=empty',
        ),
        'students_in_subject_groups': _health_metric(
            label='Students placed in subject groups',
            assigned=placed,
            total=required,
            href='/classes?tab=subjects',
        ),
    }


def _setup_health(*, school, term, class_stats) -> dict:
    total_classes = class_stats['total_classes']
    assigned_classes = class_stats['assigned_classes']
    classes_with_students = class_stats['classes_with_students']
    total_subjects = class_stats['total_class_subjects']
    assigned_subjects = class_stats['assigned_class_subjects']

    return {
        'class_teachers': _health_metric(
            label='Classes with a class teacher',
            assigned=assigned_classes,
            total=total_classes,
            href='/classes?tab=classes&attention=unassigned',
        ),
        'subject_teachers': _health_metric(
            label='Subjects with a subject teacher',
            assigned=assigned_subjects,
            total=total_subjects,
            href='/classes?tab=subjects&attention=unassigned',
        ),
        'classes_with_students': _health_metric(
            label='Classes with students',
            assigned=classes_with_students,
            total=total_classes,
            href='/classes?tab=classes&attention=empty',
        ),
        **_subject_group_health(school=school, term=term),
    }


def _academic_progress(*, school, assessment) -> list[dict]:
    level_by_class = {
        str(item.id): {
            'level_id': str(item.level_id),
            'level_name': item.level.name,
        }
        for item in ClassLevel.objects.filter(school=school, is_active=True).select_related(
            'level',
        )
    }

    progress = []
    for row in assessment['results']:
        students = row['students_count']
        if students <= 0:
            continue
        ready = row['ready_for_you_count']
        released = row['released_count']
        completed = ready + released
        level_info = level_by_class.get(row['class_level_id'], {})
        progress.append({
            'stream_id': row['stream_id'],
            'class_level_id': row['class_level_id'],
            'level_id': level_info.get('level_id'),
            'level_name': level_info.get('level_name'),
            'display_name': row['display_name'],
            'students_count': students,
            'ready_count': ready,
            'released_count': released,
            'completed_count': completed,
            'ready_percent': _percent(ready, students),
            'released_percent': _percent(released, students),
            'percent_complete': _percent(completed, students),
        })
    return progress


def _levels_for_progress(*, school, assessment) -> list[dict]:
    level_by_class = {
        str(item.id): item.level
        for item in ClassLevel.objects.filter(school=school, is_active=True).select_related(
            'level',
        )
    }
    levels_by_id = {}
    for row in assessment['results']:
        if row['students_count'] <= 0:
            continue
        level = level_by_class.get(row['class_level_id'])
        if level is None:
            continue
        levels_by_id[str(level.id)] = level

    return [
        {'id': str(level.id), 'name': level.name}
        for level in sorted(levels_by_id.values(), key=lambda item: (item.order, item.name))
    ]
