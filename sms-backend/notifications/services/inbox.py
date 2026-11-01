"""Read and mark personal notifications for a membership."""

from django.utils import timezone
from rest_framework.exceptions import NotFound

from notifications.models import Notification


def list_notifications(*, membership, unread_only: bool = False):
    queryset = Notification.objects.filter(recipient=membership).select_related(
        'actor',
        'activity',
    )
    if unread_only:
        queryset = queryset.filter(read_at__isnull=True)
    return queryset.order_by('-created_at')


def unread_count(*, membership) -> int:
    return Notification.objects.filter(recipient=membership, read_at__isnull=True).count()


def mark_notification_read(*, membership, notification_id) -> Notification:
    notification = (
        Notification.objects.filter(id=notification_id, recipient=membership).first()
    )
    if notification is None:
        raise NotFound('Notification not found.')
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=['read_at', 'updated_at'])
    return notification


def mark_all_read(*, membership) -> int:
    now = timezone.now()
    return Notification.objects.filter(
        recipient=membership,
        read_at__isnull=True,
    ).update(read_at=now, updated_at=now)
