"""Create in-app notification rows for one or more memberships."""

from django.conf import settings
from django.db import transaction

from notifications.models import Notification


def _queue_email_if_needed(notification: Notification) -> None:
    """Mark pending and enqueue Celery delivery when email is configured + present."""
    if not getattr(settings, 'EMAIL_ENABLED', False):
        return

    email = (getattr(notification.recipient.user, 'email', None) or '').strip()
    if not email:
        return

    notification.email_status = Notification.EmailStatus.PENDING
    notification.save(update_fields=['email_status', 'updated_at'])

    notification_id = str(notification.id)

    def enqueue():
        from notifications.tasks import deliver_notification_email_task

        deliver_notification_email_task.delay(notification_id)

    transaction.on_commit(enqueue)


def notify(
    *,
    school,
    recipient,
    event_type: str,
    title: str,
    body: str,
    href: str = '',
    actor=None,
    target_kind: str = '',
    target_id=None,
    activity=None,
) -> Notification | None:
    """Insert one notification. Skips if recipient is missing or is the actor."""
    if recipient is None:
        return None
    if actor is not None and recipient.user_id == getattr(actor, 'id', actor):
        return None
    if not recipient.is_active:
        return None

    # Ensure user (and email) is available for delivery checks.
    from accounts.models import SchoolMembership

    if getattr(recipient, 'user', None) is None:
        recipient = SchoolMembership.objects.select_related('user').get(pk=recipient.pk)

    notification = Notification.objects.create(
        school=school,
        recipient=recipient,
        actor=actor,
        event_type=event_type,
        title=title[:200],
        body=body[:500],
        href=href or '',
        target_kind=target_kind or '',
        target_id=target_id,
        activity=activity,
        email_status=Notification.EmailStatus.SKIPPED,
    )
    _queue_email_if_needed(notification)
    return notification


def notify_many(
    *,
    school,
    recipients,
    event_type: str,
    title: str,
    body: str,
    href: str = '',
    actor=None,
    target_kind: str = '',
    target_id=None,
    activity=None,
) -> list[Notification]:
    """Fan out the same notice to many memberships (deduped by id)."""
    seen = set()
    created = []
    for recipient in recipients:
        if recipient is None:
            continue
        if recipient.id in seen:
            continue
        seen.add(recipient.id)
        row = notify(
            school=school,
            recipient=recipient,
            event_type=event_type,
            title=title,
            body=body,
            href=href,
            actor=actor,
            target_kind=target_kind,
            target_id=target_id,
            activity=activity,
        )
        if row is not None:
            created.append(row)
    return created
