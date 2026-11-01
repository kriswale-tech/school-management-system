"""Celery tasks for students domain."""

from celery import shared_task


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
    name='students.notify_bulk_ward_enrolled',
)
def notify_bulk_ward_enrolled_task(self, notices: list) -> dict:
    """Send ward-enrolled guardian notices for bulk-imported students.

    ``notices``: list of ``{'student_id': str, 'class_name': str}``.
    """
    from notifications.services.guardians import notify_guardians_ward_enrolled
    from students.models import Student

    notified = 0
    skipped = 0
    for notice in notices or []:
        student_id = notice.get('student_id')
        if not student_id:
            skipped += 1
            continue
        student = (
            Student.objects.select_related('school')
            .filter(id=student_id)
            .first()
        )
        if student is None:
            skipped += 1
            continue
        result = notify_guardians_ward_enrolled(
            student=student,
            class_name=notice.get('class_name') or '',
        )
        if result.get('sms') or result.get('email'):
            notified += 1
        else:
            skipped += 1

    return {
        'requested': len(notices or []),
        'notified': notified,
        'skipped': skipped,
    }
