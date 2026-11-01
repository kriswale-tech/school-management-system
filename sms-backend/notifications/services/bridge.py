"""Map activity feed rows onto personal notifications (Tier 1)."""

from activities.models import Activity
from notifications.models import Notification
from notifications.services import emit, recipients

# Activity verbs that should fan out to an inbox. Fee / subject-group noise stays
# on the activity feed only until a later phase.
AUTO_NOTIFY_VERBS = frozenset({
    Activity.Verb.SCORES_PUBLISHED,
    Activity.Verb.STUDENTS_APPROVED,
    Activity.Verb.STUDENT_REJECTED,
    Activity.Verb.REOPEN_REQUESTED,
    Activity.Verb.REPORTS_RELEASED,
    Activity.Verb.CORRECTION_SENT,
    Activity.Verb.CORRECTION_APPLIED,
    Activity.Verb.REOPEN_DECLINED,
    Activity.Verb.CLASS_TEACHER_ASSIGNED,
    Activity.Verb.SUBJECT_TEACHER_ASSIGNED,
    Activity.Verb.STUDENT_ENROLLED,
    Activity.Verb.STUDENT_LEFT,
    Activity.Verb.STUDENT_REACTIVATED,
    Activity.Verb.STUDENT_UPDATED,
    Activity.Verb.GUARDIAN_UPDATED,
    Activity.Verb.MEMBER_INVITED,
    Activity.Verb.MEMBER_UPDATED,
    Activity.Verb.MEMBER_PHONE_CHANGED,
    Activity.Verb.MEMBER_ROLE_CHANGED,
    Activity.Verb.TERM_OPENED,
})

_TITLES = {
    Activity.Verb.SCORES_PUBLISHED: 'Scores published',
    Activity.Verb.STUDENTS_APPROVED: 'Students approved',
    Activity.Verb.STUDENT_REJECTED: 'Student rejected',
    Activity.Verb.REOPEN_REQUESTED: 'Reopen requested',
    Activity.Verb.REPORTS_RELEASED: 'Reports released',
    Activity.Verb.CORRECTION_SENT: 'Correction needed',
    Activity.Verb.CORRECTION_APPLIED: 'Correction applied',
    Activity.Verb.REOPEN_DECLINED: 'Reopen declined',
    Activity.Verb.CLASS_TEACHER_ASSIGNED: 'Class teacher assignment',
    Activity.Verb.SUBJECT_TEACHER_ASSIGNED: 'Subject assignment',
    Activity.Verb.STUDENT_ENROLLED: 'New enrollment',
    Activity.Verb.STUDENT_LEFT: 'Student left',
    Activity.Verb.STUDENT_REACTIVATED: 'Student reactivated',
    Activity.Verb.STUDENT_UPDATED: 'Student profile updated',
    Activity.Verb.GUARDIAN_UPDATED: 'Guardian updated',
    Activity.Verb.MEMBER_INVITED: 'Added to school',
    Activity.Verb.MEMBER_UPDATED: 'Your profile was updated',
    Activity.Verb.MEMBER_PHONE_CHANGED: 'Phone number changed',
    Activity.Verb.MEMBER_ROLE_CHANGED: 'Your role changed',
    Activity.Verb.TERM_OPENED: 'New term opened',
}


def notify_for_activity(activity, *, extra_recipients=None) -> list[Notification]:
    """Create inbox rows for an activity when the verb is in the Tier‑1 set."""
    if activity is None or activity.verb not in AUTO_NOTIFY_VERBS:
        return []

    resolved = list(_recipients_for(activity))
    if extra_recipients:
        resolved.extend(extra_recipients)

    return emit.notify_many(
        school=activity.school,
        recipients=resolved,
        event_type=activity.verb,
        title=_TITLES.get(activity.verb, 'Notification'),
        body=activity.summary,
        href=activity.href,
        actor=activity.actor,
        target_kind=activity.target_kind,
        target_id=activity.target_id,
        activity=activity,
    )


def _as_list(queryset):
    return list(queryset)


def _recipients_for(activity):
    school = activity.school
    stream = activity.stream
    term = activity.term
    verb = activity.verb
    actor = activity.actor
    rows: list = []

    if verb == Activity.Verb.SCORES_PUBLISHED:
        rows = _as_list(
            recipients.class_teacher_memberships(school=school, term=term, stream=stream)
        )
    elif verb == Activity.Verb.STUDENTS_APPROVED:
        rows = _as_list(recipients.admins_and_staff(school))
    elif verb == Activity.Verb.REPORTS_RELEASED:
        rows = _as_list(
            recipients.class_teacher_memberships(school=school, term=term, stream=stream)
        )
    elif verb in (
        Activity.Verb.STUDENT_REJECTED,
        Activity.Verb.CORRECTION_SENT,
        Activity.Verb.CORRECTION_APPLIED,
    ):
        if activity.teaching_assignment_id:
            assignment = activity.teaching_assignment
            if assignment is not None:
                rows.extend(
                    _as_list(
                        recipients.teacher_memberships_for_users(
                            school,
                            [assignment.teacher_id],
                        )
                    )
                )
        rows.extend(
            _as_list(
                recipients.class_teacher_memberships(school=school, term=term, stream=stream)
            )
        )
    elif verb == Activity.Verb.REOPEN_REQUESTED:
        rows = _as_list(recipients.admins_and_staff(school))
    elif verb == Activity.Verb.REOPEN_DECLINED:
        rows = _as_list(
            recipients.class_teacher_memberships(school=school, term=term, stream=stream)
        )
    elif verb == Activity.Verb.CLASS_TEACHER_ASSIGNED:
        from teachers.models import ClassTeacher

        if term is not None and stream is not None:
            teacher_ids = ClassTeacher.objects.filter(
                term=term,
                stream_id=stream.id,
            ).values_list('teacher_id', flat=True)
            rows = _as_list(recipients.teacher_memberships_for_users(school, teacher_ids))
    elif verb == Activity.Verb.SUBJECT_TEACHER_ASSIGNED:
        if activity.teaching_assignment_id and activity.teaching_assignment is not None:
            rows = _as_list(
                recipients.teacher_memberships_for_users(
                    school,
                    [activity.teaching_assignment.teacher_id],
                )
            )
    elif verb in (
        Activity.Verb.STUDENT_ENROLLED,
        Activity.Verb.STUDENT_LEFT,
        Activity.Verb.STUDENT_REACTIVATED,
        Activity.Verb.STUDENT_UPDATED,
        Activity.Verb.GUARDIAN_UPDATED,
    ):
        rows = _as_list(recipients.admins_and_staff(school))
        rows.extend(
            _as_list(
                recipients.class_teacher_memberships(school=school, term=term, stream=stream)
            )
        )
    elif verb == Activity.Verb.TERM_OPENED:
        rows = _as_list(recipients.all_active_members(school))
    # Member identity events rely on extra_recipients from the caller.

    if actor is not None:
        rows = [row for row in rows if row.user_id != actor.id]
    return rows
