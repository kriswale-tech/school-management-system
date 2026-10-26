"""School-wide staff dashboard — academics and people, no fees."""

from __future__ import annotations

from academics.services.classes import get_class_stats
from accounts.models import SchoolMembership, User
from activities.services import list_activities_for_staff
from assessments.services.admin_overview import list_admin_assessment_overview
from dashboard.services.admin_dashboard import _build_needs_attention
from schools.models import Term
from students.services import get_student_stats


def get_staff_dashboard(*, school) -> dict:
    term = (
        Term.objects.filter(school=school, is_active=True)
        .select_related('academic_year')
        .first()
    )
    teachers_count = SchoolMembership.objects.filter(
        school=school,
        is_active=True,
        role=User.RoleChoices.TEACHER,
    ).count()

    if term is None:
        return _empty_dashboard(teachers_count=teachers_count)

    class_stats = get_class_stats(school=school, term=term)
    student_stats = get_student_stats(school=school, term=term)
    assessment = list_admin_assessment_overview(school=school, term_id=term.id)

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
            pending > 0,
        )
    )

    needs_attention = _build_needs_attention(
        ready_for_you=ready,
        unassigned_classes=class_stats['unassigned_classes'],
        debtors_count=0,
        unassigned_subjects=class_stats['unassigned_class_subjects'],
        corrections_inbox=inbox_count,
        empty_classes=class_stats['empty_classes'],
        needs_correction=needs_correction,
    )

    activities = list(
        list_activities_for_staff(school=school, term=term)[:10],
    )

    return {
        'term_id': str(term.id),
        'term_label': f'{term.academic_year.academic_year} · {term.get_term_display()}',
        'show_academic_widgets': show_academic_widgets,
        'school_overview': {
            'total_students': student_stats['total_students'],
            'total_classes': class_stats['total_classes'],
            'teachers_count': teachers_count,
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
        'activities': activities,
    }


def _empty_dashboard(*, teachers_count: int) -> dict:
    return {
        'term_id': None,
        'term_label': None,
        'show_academic_widgets': False,
        'school_overview': {
            'total_students': 0,
            'total_classes': 0,
            'teachers_count': teachers_count,
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
        'activities': [],
    }
