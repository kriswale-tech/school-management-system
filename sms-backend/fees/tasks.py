"""Celery tasks for fees domain (guardian notices)."""

from celery import shared_task


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
    name='fees.notify_fee_structure_applied',
)
def notify_fee_structure_applied_task(self, fee_structure_id: str) -> dict:
    from fees.services.next_term_notices import process_fee_structure_applied_notices

    return process_fee_structure_applied_notices(fee_structure_id=fee_structure_id)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
    name='fees.notify_student_fee_schedule',
)
def notify_student_fee_schedule_task(self, student_id: str, term_id: str) -> dict:
    from fees.services.next_term_notices import process_student_fee_schedule_notice

    return process_student_fee_schedule_notice(student_id=student_id, term_id=term_id)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
    name='fees.run_auto_debt_reminders',
)
def run_auto_debt_reminders_task(self) -> dict:
    """Beat entrypoint: enqueue per-school auto debt reminder jobs that are due today."""
    from fees.services.auto_debt_reminders import run_auto_debt_reminders

    return run_auto_debt_reminders()


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
    name='fees.process_school_auto_debt_reminders',
)
def process_school_auto_debt_reminders_task(self, school_id: str, today_iso: str | None = None) -> dict:
    from datetime import date

    from fees.services.auto_debt_reminders import process_school_auto_debt_reminders

    today = date.fromisoformat(today_iso) if today_iso else None
    return process_school_auto_debt_reminders(school_id=school_id, today=today)
