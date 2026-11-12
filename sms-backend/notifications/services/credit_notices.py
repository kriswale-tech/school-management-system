"""Tell school staff when a send could not be fully covered by credits."""

from accounts.models import SchoolMembership, User
from notifications.models import Notification
from notifications.services.emit import notify_many


def notify_messaging_credit_shortfall(*, school, channel: str, skipped: int) -> None:
    skipped = int(skipped or 0)
    if skipped < 1:
        return
    label = 'SMS' if channel == 'sms' else 'Email'
    noun = 'message' if skipped == 1 else 'messages'
    recipients = SchoolMembership.objects.filter(
        school=school,
        is_active=True,
        role__in=[User.RoleChoices.ADMIN, User.RoleChoices.STAFF],
    ).select_related('user')
    notify_many(
        school=school,
        recipients=recipients,
        event_type=Notification.EventType.MESSAGING_CREDITS,
        title=f'{label} credits ran short',
        body=(
            f'{skipped} {label} {noun} were not sent because credits were not enough. '
            f'Buy credits, then resend the skipped messages from Messaging.'
        ),
        href=f'/settings/messaging?view=history&status=skipped&channel={channel}',
    )


def notify_sms_provider_unavailable(*, school, skipped: int) -> None:
    """School staff notice when the platform SMS wallet cannot cover a send."""
    skipped = int(skipped or 0)
    if skipped < 1:
        return
    noun = 'message' if skipped == 1 else 'messages'
    recipients = SchoolMembership.objects.filter(
        school=school,
        is_active=True,
        role__in=[User.RoleChoices.ADMIN, User.RoleChoices.STAFF],
    ).select_related('user')
    notify_many(
        school=school,
        recipients=recipients,
        event_type=Notification.EventType.MESSAGING_CREDITS,
        title='SMS is temporarily unavailable',
        body=(
            f'{skipped} SMS {noun} were not sent because SMS is temporarily unavailable. '
            'Your credits were not used. Resend the skipped messages from Messaging '
            'once SMS is available.'
        ),
        href='/settings/messaging?view=history&status=skipped&channel=sms',
    )
