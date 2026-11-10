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


@shared_task(name='notifications.poll_pending_sms_status')
def poll_pending_sms_status_task(
    older_than_seconds: int = 180,
    limit: int = 100,
) -> dict:
    """Fallback DLR poll for SMS still awaiting a final provider status."""
    import logging

    from requests.exceptions import RequestException

    from notifications.services.sms_status import apply_provider_status, pending_sms_for_poll
    from shared.services.arkesel_sms import extract_status_from_lookup, get_sms_status

    logger = logging.getLogger(__name__)
    checked = 0
    updated = 0
    errors = 0
    for delivery in pending_sms_for_poll(
        older_than_seconds=older_than_seconds,
        limit=limit,
    ):
        checked += 1
        try:
            payload = get_sms_status(delivery.provider_message_id)
            status_value = extract_status_from_lookup(payload)
            if not status_value:
                logger.info(
                    'No status in Arkesel lookup for delivery=%s id=%s',
                    delivery.pk,
                    delivery.provider_message_id,
                )
                continue
            row = apply_provider_status(
                sms_id=delivery.provider_message_id,
                provider_status=status_value,
                source='poll',
            )
            if row is not None and row.status != delivery.status:
                updated += 1
        except RequestException as exc:
            errors += 1
            logger.warning(
                'Arkesel status poll failed for delivery=%s: %s',
                delivery.pk,
                exc,
            )
        except Exception:
            errors += 1
            logger.exception('Unexpected poll error for delivery=%s', delivery.pk)
    return {'checked': checked, 'updated': updated, 'errors': errors}
