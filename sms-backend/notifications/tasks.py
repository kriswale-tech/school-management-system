"""Celery tasks for notification and guardian outbound delivery."""

from celery import shared_task


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
    name='notifications.deliver_notification_email',
)
def deliver_notification_email_task(self, notification_id: str) -> str:
    from notifications.services.send_email import deliver_notification_email

    return deliver_notification_email(notification_id)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
    name='notifications.deliver_guardian_sms_batch',
)
def deliver_guardian_sms_batch_task(self, items: list) -> dict:
    from notifications.services.deliver_guardian import deliver_guardian_sms_batch

    return deliver_guardian_sms_batch(items)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
    name='notifications.deliver_guardian_email_batch',
)
def deliver_guardian_email_batch_task(self, items: list) -> dict:
    from notifications.services.deliver_guardian import deliver_guardian_email_batch

    return deliver_guardian_email_batch(items)
