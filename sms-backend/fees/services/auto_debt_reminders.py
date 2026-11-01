"""Scheduled (Celery beat) guardian debt reminders."""

from __future__ import annotations

import calendar
import logging
from datetime import date
from decimal import Decimal

from django.db.models import F
from django.utils import timezone

from fees.services.desk import list_fee_desk_rows
from fees.services.fees import get_student_term_balance
from notifications.models import GuardianDelivery
from notifications.services import guardians as guardian_services
from notifications.services.outbound import enqueue_guardian_outbound
from schools.models import School, SchoolSettings
from schools.services.settings import get_school_settings
from students.models import Student
from students.services import resolve_term

logger = logging.getLogger(__name__)

STUDENT_PLAN_CHUNK = 200


def auto_debt_reminder_period_key(frequency: str, today: date) -> str:
    """Stable period id used in batch/idempotency keys for a given run."""
    if frequency == SchoolSettings.DebtReminderFrequency.END_OF_MONTH:
        return today.strftime('%Y-%m')
    if frequency == SchoolSettings.DebtReminderFrequency.WEEKLY:
        return today.strftime('%G-W%V')
    if frequency == SchoolSettings.DebtReminderFrequency.BIWEEKLY:
        iso = today.isocalendar()
        return f'{iso.year}-B{iso.week // 2:02d}'
    return today.isoformat()


def is_auto_debt_reminder_due(*, frequency: str, today: date) -> bool:
    """Whether *today* is a send day for the school frequency."""
    if frequency == SchoolSettings.DebtReminderFrequency.END_OF_MONTH:
        last_day = calendar.monthrange(today.year, today.month)[1]
        return today.day == last_day
    if frequency == SchoolSettings.DebtReminderFrequency.WEEKLY:
        return today.weekday() == 0  # Monday
    if frequency == SchoolSettings.DebtReminderFrequency.BIWEEKLY:
        # Mondays on even ISO week numbers (stable across years within the year).
        return today.weekday() == 0 and today.isocalendar().week % 2 == 0
    return False


def schools_due_for_auto_debt_reminders(*, today: date | None = None) -> list[School]:
    today = today or timezone.localdate()
    rows = (
        SchoolSettings.objects.filter(
            guardian_debt_reminder_enabled=True,
            guardian_debt_reminder_auto_enabled=True,
        )
        .select_related('school')
    )
    due = []
    for settings_row in rows:
        if is_auto_debt_reminder_due(
            frequency=settings_row.guardian_debt_reminder_frequency,
            today=today,
        ):
            due.append(settings_row.school)
    return due


def process_school_auto_debt_reminders(
    *,
    school_id,
    today: date | None = None,
) -> dict:
    """Find active-term debtors and enqueue guardian reminders for one school."""
    today = today or timezone.localdate()
    school = School.objects.filter(id=school_id).first()
    if school is None:
        return {'queued_students': 0, 'sms': 0, 'email': 0, 'skipped': 'school_missing'}

    preferences = get_school_settings(school)
    if (
        not preferences.guardian_debt_reminder_enabled
        or not preferences.guardian_debt_reminder_auto_enabled
    ):
        return {'queued_students': 0, 'sms': 0, 'email': 0, 'skipped': 'disabled'}

    if not is_auto_debt_reminder_due(
        frequency=preferences.guardian_debt_reminder_frequency,
        today=today,
    ):
        return {'queued_students': 0, 'sms': 0, 'email': 0, 'skipped': 'not_due'}

    try:
        term = resolve_term(school, None)
    except Exception:
        logger.info('No active term for school %s; skipping auto debt reminders', school_id)
        return {'queued_students': 0, 'sms': 0, 'email': 0, 'skipped': 'no_active_term'}

    period = auto_debt_reminder_period_key(
        preferences.guardian_debt_reminder_frequency,
        today,
    )
    batch_id = f'auto-{school.id}-{term.id}-{period}'
    threshold = preferences.fees_alert_threshold or Decimal('0.00')

    debtor_ids = list(
        list_fee_desk_rows(school=school, term=term)
        .filter(total_billed__gt=F('total_paid'))
        .values_list('student_id', flat=True),
    )
    if not debtor_ids:
        return {
            'queued_students': 0,
            'sms': 0,
            'email': 0,
            'period': period,
            'term_id': str(term.id),
        }

    sms_items: list[dict] = []
    email_items: list[dict] = []
    students_queued = 0

    for start in range(0, len(debtor_ids), STUDENT_PLAN_CHUNK):
        chunk_ids = debtor_ids[start:start + STUDENT_PLAN_CHUNK]
        students = {
            str(student.id): student
            for student in Student.objects.filter(
                school=school,
                id__in=chunk_ids,
            ).select_related('school')
        }
        for student_id in chunk_ids:
            student = students.get(str(student_id))
            if student is None:
                continue
            balance = get_student_term_balance(student=student, term=term)['balance']
            if balance <= 0 or balance < threshold:
                continue
            planned_sms, planned_email = guardian_services.plan_guardians_debt_reminder(
                student=student,
                term=term,
                balance=balance,
                batch_id=batch_id,
            )
            if planned_sms or planned_email:
                students_queued += 1
            sms_items.extend(planned_sms)
            email_items.extend(planned_email)

    queued = enqueue_guardian_outbound(sms_items=sms_items, email_items=email_items)
    logger.info(
        'Auto debt reminders school=%s period=%s students=%s sms=%s email=%s',
        school_id,
        period,
        students_queued,
        queued['sms'],
        queued['email'],
    )
    return {
        'queued_students': students_queued,
        'sms': queued['sms'],
        'email': queued['email'],
        'period': period,
        'term_id': str(term.id),
        'batch_id': batch_id,
        'event_type': GuardianDelivery.EventType.DEBT_REMINDER,
    }


def run_auto_debt_reminders(*, today: date | None = None) -> dict:
    """Fan out per-school auto reminder jobs (called from Celery beat)."""
    today = today or timezone.localdate()
    schools = schools_due_for_auto_debt_reminders(today=today)
    from fees.tasks import process_school_auto_debt_reminders_task

    for school in schools:
        process_school_auto_debt_reminders_task.delay(str(school.id), today.isoformat())
    return {
        'date': today.isoformat(),
        'schools_due': len(schools),
        'school_ids': [str(school.id) for school in schools],
    }
