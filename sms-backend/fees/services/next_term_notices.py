"""Guardian notices after fee structures are applied (per-student schedules)."""

from __future__ import annotations

import logging

from django.db import transaction

from fees.models import FeeStructure, StudentFee
from notifications.models import GuardianDelivery
from notifications.services import guardians as guardian_services
from notifications.services.outbound import enqueue_guardian_outbound
from schools.services.settings import get_school_settings
from students.models import Student

logger = logging.getLogger(__name__)


def schedule_next_term_fee_notices_for_structure(*, fee_structure_id) -> None:
    """Enqueue Celery planning after the apply transaction commits."""

    def _run():
        from fees.tasks import notify_fee_structure_applied_task

        notify_fee_structure_applied_task.delay(str(fee_structure_id))

    transaction.on_commit(_run)


def schedule_next_term_fee_notice_for_student(*, student_id, term_id) -> None:
    """Enqueue a single-student notice (e.g. late enrollment after apply)."""

    def _run():
        from fees.tasks import notify_student_fee_schedule_task

        notify_student_fee_schedule_task.delay(str(student_id), str(term_id))

    transaction.on_commit(_run)


def process_fee_structure_applied_notices(*, fee_structure_id: str) -> dict:
    """Plan + enqueue guardian notices for every student billed by this structure."""
    fee_structure = (
        FeeStructure.objects.select_related(
            'school',
            'term',
            'term__academic_year',
        )
        .filter(id=fee_structure_id)
        .first()
    )
    if fee_structure is None:
        logger.warning('Fee structure %s missing for next-term notices', fee_structure_id)
        return {'students_queued': 0, 'sms': 0, 'email': 0}

    preferences = get_school_settings(fee_structure.school)
    policy = guardian_services._event_policy(
        preferences,
        GuardianDelivery.EventType.NEXT_TERM_FEES,
    )
    if policy is None or not policy.enabled:
        return {'students_queued': 0, 'sms': 0, 'email': 0}

    student_ids = list(
        StudentFee.objects.filter(fee_structure=fee_structure)
        .values_list('student_id', flat=True)
        .distinct(),
    )
    if not student_ids:
        return {'students_queued': 0, 'sms': 0, 'email': 0}

    students = {
        str(student.id): student
        for student in Student.objects.filter(
            school=fee_structure.school,
            id__in=student_ids,
        ).select_related('school')
    }

    sms_items: list[dict] = []
    email_items: list[dict] = []
    students_queued = 0
    for student_id in student_ids:
        student = students.get(str(student_id))
        if student is None:
            continue
        planned_sms, planned_email = guardian_services.plan_guardians_next_term_fees(
            student=student,
            term=fee_structure.term,
            fee_structure=fee_structure,
        )
        if planned_sms or planned_email:
            students_queued += 1
        sms_items.extend(planned_sms)
        email_items.extend(planned_email)

    queued = enqueue_guardian_outbound(sms_items=sms_items, email_items=email_items)
    return {
        'students_queued': students_queued,
        'sms': queued['sms'],
        'email': queued['email'],
    }


def process_student_fee_schedule_notice(*, student_id: str, term_id: str) -> dict:
    """Plan + enqueue notice for one student/term (late enrollment)."""
    student = (
        Student.objects.select_related('school')
        .filter(id=student_id)
        .first()
    )
    if student is None:
        return {'students_queued': 0, 'sms': 0, 'email': 0}

    preferences = get_school_settings(student.school)
    policy = guardian_services._event_policy(
        preferences,
        GuardianDelivery.EventType.NEXT_TERM_FEES,
    )
    if policy is None or not policy.enabled:
        return {'students_queued': 0, 'sms': 0, 'email': 0}

    fee_structure = (
        FeeStructure.objects.select_related('term', 'term__academic_year')
        .filter(
            school=student.school,
            term_id=term_id,
            status=FeeStructure.Status.APPLIED,
        )
        .first()
    )
    if fee_structure is None:
        return {'students_queued': 0, 'sms': 0, 'email': 0}

    if not StudentFee.objects.filter(student=student, term_id=term_id).exists():
        return {'students_queued': 0, 'sms': 0, 'email': 0}

    sms_items, email_items = guardian_services.plan_guardians_next_term_fees(
        student=student,
        term=fee_structure.term,
        fee_structure=fee_structure,
    )
    queued = enqueue_guardian_outbound(sms_items=sms_items, email_items=email_items)
    return {
        'students_queued': 1 if (sms_items or email_items) else 0,
        'sms': queued['sms'],
        'email': queued['email'],
    }
