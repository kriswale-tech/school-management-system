"""Teacher dashboard for the classes and subjects assigned this term."""

from __future__ import annotations

from django.db.models import Count

from accounts.services.staff_desk import serialize_teacher_assignments
from activities.services import list_activities_for_teacher
from schools.models import Term


def get_teacher_dashboard(*, school, membership) -> dict:
    user = membership.user
    term = (
        Term.objects.filter(school=school, is_active=True)
        .select_related('academic_year')
        .first()
    )
    assignments = serialize_teacher_assignments(user=user, school=school)
    class_rows = assignments['class_teacher_assignments']
    subject_rows = assignments['teaching_assignments']
    is_class_teacher = bool(class_rows)
    is_subject_teacher = bool(subject_rows)

    overview = _class_overview(school=school, membership=membership, enabled=is_class_teacher)
    subjects = _subject_rows(subject_rows)
    show_academic = _show_academic(overview=overview, subjects=subjects)
    classes = _class_rows(overview['results'])
    activities = []
    if term is not None:
        activities = list(
            list_activities_for_teacher(school=school, user=user, term=term)[:10]
        )
    subjects_to_publish = sum(1 for row in subjects if row['is_open'])
    subjects_published = sum(
        1 for row in subjects if row['students_count'] > 0 and not row['is_open']
    )

    return {
        'is_class_teacher': is_class_teacher,
        'is_subject_teacher': is_subject_teacher,
        'show_academic_widgets': show_academic,
        'classes_overview': {
            'classes_count': len(classes),
            'students_count': sum(row['students_count'] for row in classes),
        },
        'subjects_overview': {
            'subjects_count': len(subjects),
            'students_count': sum(row['students_count'] for row in subjects),
        },
        'academic_overview': {
            'pending_reports': overview['pending_count'],
            'awaiting_approval': overview['awaiting_approval_count'],
            'approved_reports': overview['approved_count'],
            'subjects_to_publish': subjects_to_publish,
            'subjects_published': subjects_published,
            'corrections_count': assignments['corrections_inbox_count'],
        },
        'needs_attention': _needs_attention(classes=classes, subjects=subjects),
        'classes': classes,
        'subjects': subjects,
        'activities': activities,
    }


def _class_overview(*, school, membership, enabled):
    empty = {
        'pending_count': 0,
        'awaiting_approval_count': 0,
        'approved_count': 0,
        'needs_correction_count': 0,
        'results': [],
    }
    if not enabled:
        return empty
    from assessments.services.class_overview import list_class_teacher_assessment_overview

    overview = list_class_teacher_assessment_overview(school=school, membership=membership)
    return {
        'pending_count': overview['pending_count'],
        'awaiting_approval_count': overview['awaiting_approval_count'],
        'approved_count': overview['approved_count'],
        'needs_correction_count': overview['needs_correction_count'],
        'results': overview['results'],
    }


def _subject_rows(subject_rows):
    from assessments.models import SubjectScore

    ids = [row['id'] for row in subject_rows]
    published = {}
    if ids:
        published = {
            row['teaching_assignment_id']: row['published_count']
            for row in SubjectScore.objects.filter(
                teaching_assignment_id__in=ids,
                is_published=True,
            )
            .values('teaching_assignment_id')
            .annotate(published_count=Count('id'))
        }

    ready_to_publish = _ready_to_publish_counts(subject_rows)
    unplaced = _unplaced_counts(subject_rows)

    rows = []
    for row in subject_rows:
        students_count = row['students_count']
        published_count = published.get(row['id'], 0)
        rows.append({
            'id': str(row['id']),
            'subject_name': row['subject_name'],
            'display_class_name': row['display_class_name'],
            'subject_group_name': row['subject_group_name'],
            'students_count': students_count,
            'published_count': published_count,
            'is_open': students_count > 0 and published_count < students_count,
            'ready_to_publish_count': ready_to_publish.get(row['id'], 0),
            'unplaced_count': unplaced.get(row['id'], 0),
            'needs_correction_count': row['needs_correction_count'],
            'href': f'/classes/subjects/{row["id"]}',
        })
    return rows


def _ready_to_publish_counts(subject_rows):
    """Students with a full class score and exam who are still unpublished.

    Students already sent back for correction are left to that queue.
    """
    from academics.services.teaching_assignments import _enrollment_queryset
    from assessments.models import (
        AssessmentItem,
        AssessmentItemScore,
        CorrectionRequest,
        CorrectionRequestSubject,
        SubjectScore,
    )
    from teachers.models import TeachingAssignment

    ids = [row['id'] for row in subject_rows]
    if not ids:
        return {}

    assignments = {
        assignment.id: assignment
        for assignment in TeachingAssignment.objects.filter(id__in=ids).select_related(
            'class_subject',
            'term',
            'stream',
            'subject_group',
        )
    }
    item_counts = {
        row['teaching_assignment_id']: row['item_count']
        for row in AssessmentItem.objects.filter(teaching_assignment_id__in=ids)
        .values('teaching_assignment_id')
        .annotate(item_count=Count('id'))
    }
    complete_class_scores = set()
    for row in (
        AssessmentItemScore.objects.filter(
            assessment_item__teaching_assignment_id__in=ids,
        )
        .values('assessment_item__teaching_assignment_id', 'student_id')
        .annotate(mark_count=Count('id'))
    ):
        assignment_id = row['assessment_item__teaching_assignment_id']
        required = item_counts.get(assignment_id, 0)
        if required and row['mark_count'] >= required:
            complete_class_scores.add((assignment_id, row['student_id']))

    exams = set(
        SubjectScore.objects.filter(
            teaching_assignment_id__in=ids,
            is_published=False,
            exam_mark__isnull=False,
        ).values_list('teaching_assignment_id', 'student_id')
    )
    in_correction = set(
        CorrectionRequestSubject.objects.filter(
            teaching_assignment_id__in=ids,
            correction_request__status=CorrectionRequest.Status.APPLIED,
        ).values_list('teaching_assignment_id', 'correction_request__student_id')
    )

    counts = {}
    for assignment in assignments.values():
        if not item_counts.get(assignment.id):
            counts[assignment.id] = 0
            continue
        roster = set(
            _enrollment_queryset(assignment=assignment).values_list('student_id', flat=True)
        )
        counts[assignment.id] = sum(
            1
            for student_id in roster
            if (assignment.id, student_id) in complete_class_scores
            and (assignment.id, student_id) in exams
            and (assignment.id, student_id) not in in_correction
        )
    return counts


def _unplaced_counts(subject_rows):
    """Enrolled students with no group on a subject this teacher teaches as a group."""
    from academics.services.teaching_assignments import _unassigned_students_count
    from teachers.models import TeachingAssignment

    ids = [row['id'] for row in subject_rows if row.get('subject_group_id')]
    if not ids:
        return {}

    counts = {}
    for assignment in TeachingAssignment.objects.filter(id__in=ids).select_related(
        'class_subject',
        'term',
        'stream',
        'subject_group',
    ):
        counts[assignment.id] = _unassigned_students_count(assignment=assignment)
    return counts


def _show_academic(*, overview, subjects):
    if overview['awaiting_approval_count'] or overview['approved_count']:
        return True
    if overview['needs_correction_count']:
        return True
    return any(row['published_count'] > 0 for row in subjects)


def _class_rows(results):
    rows = []
    for row in results:
        view_stream_id = row.get('view_stream_id')
        rows.append({
            'id': row['id'],
            'display_name': row['display_name'],
            'students_count': row['students_count'],
            'view_stream_id': view_stream_id,
            'pending_count': row['pending_count'],
            'awaiting_approval_count': row['awaiting_approval_count'],
            'approved_count': row['approved_count'],
            'needs_correction_count': row['needs_correction_count'],
            'href': f'/assessments/{row["id"]}',
        })
    return rows


def _needs_attention(*, classes, subjects):
    items = []
    for row in classes:
        awaiting = row['awaiting_approval_count']
        if awaiting:
            label = 'student' if awaiting == 1 else 'students'
            items.append({
                'code': f'awaiting-{row["id"]}',
                'label': f'{awaiting} {label} in {row["display_name"]} ready for your approval',
                'count': awaiting,
                'href': f'/assessments/{row["id"]}',
            })
        corrections = row['needs_correction_count']
        if corrections:
            label = 'student' if corrections == 1 else 'students'
            items.append({
                'code': f'class-correction-{row["id"]}',
                'label': f'{corrections} {label} in {row["display_name"]} need correction',
                'count': corrections,
                'href': f'/assessments/{row["id"]}',
            })
    for row in subjects:
        if row['needs_correction_count']:
            count = row['needs_correction_count']
            label = 'correction' if count == 1 else 'corrections'
            items.append({
                'code': f'subject-correction-{row["id"]}',
                'label': (
                    f'Review {count} {label} in {row["subject_name"]} '
                    f'({row["display_class_name"]})'
                ),
                'count': count,
                'href': row['href'],
            })
        unplaced = row.get('unplaced_count', 0)
        if unplaced and row.get('subject_group_name'):
            label = 'student' if unplaced == 1 else 'students'
            items.append({
                'code': f'subject-unplaced-{row["id"]}',
                'label': (
                    f'Place {unplaced} {label} in {row["subject_group_name"]} '
                    f'for {row["subject_name"]}'
                ),
                'count': unplaced,
                'href': row['href'],
            })
        ready = row.get('ready_to_publish_count', 0)
        if ready:
            label = 'student' if ready == 1 else 'students'
            items.append({
                'code': f'subject-publish-{row["id"]}',
                'label': (
                    f'Publish {row["subject_name"]} scores for {row["display_class_name"]} '
                    f'({ready} {label} ready)'
                ),
                'count': ready,
                'href': row['href'],
            })
    return items
