"""Render and send a single notification email (called from Celery)."""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from notifications.models import Notification
from notifications.services.email_context import build_notification_email_context

logger = logging.getLogger(__name__)

CTA_LABELS = {
    Notification.EventType.SCORES_PUBLISHED: 'Open assessments',
    Notification.EventType.STUDENTS_APPROVED: 'Open assessments',
    Notification.EventType.STUDENT_REJECTED: 'Open assessments',
    Notification.EventType.REOPEN_REQUESTED: 'Open assessments',
    Notification.EventType.REPORTS_RELEASED: 'Open assessments',
    Notification.EventType.CORRECTION_SENT: 'Open assessments',
    Notification.EventType.CORRECTION_APPLIED: 'Open assessments',
    Notification.EventType.REOPEN_DECLINED: 'Open assessments',
    Notification.EventType.CLASS_TEACHER_ASSIGNED: 'Open class',
    Notification.EventType.SUBJECT_TEACHER_ASSIGNED: 'Open subject',
    Notification.EventType.STUDENT_ENROLLED: 'View students',
    Notification.EventType.STUDENT_LEFT: 'View student',
    Notification.EventType.STUDENT_REACTIVATED: 'View student',
    Notification.EventType.STUDENT_UPDATED: 'View student',
    Notification.EventType.GUARDIAN_UPDATED: 'View student',
    Notification.EventType.MEMBER_INVITED: 'Open the app',
    Notification.EventType.MEMBER_UPDATED: 'Open profile',
    Notification.EventType.MEMBER_PHONE_CHANGED: 'Open the app',
    Notification.EventType.MEMBER_ROLE_CHANGED: 'Open the app',
    Notification.EventType.TERM_OPENED: 'Open dashboard',
}


def recipient_email(notification: Notification) -> str:
    user = notification.recipient.user
    return (getattr(user, 'email', None) or '').strip()


def deliver_notification_email(notification_id) -> str:
    """Send one notification email and update email_status.

    Returns the resulting EmailStatus value.
    """
    notification = (
        Notification.objects.select_related(
            'school',
            'recipient',
            'recipient__user',
            'actor',
        )
        .filter(id=notification_id)
        .first()
    )
    if notification is None:
        logger.warning('Notification %s not found for email delivery', notification_id)
        return Notification.EmailStatus.FAILED

    email = recipient_email(notification)
    if not email:
        if notification.email_status != Notification.EmailStatus.SKIPPED:
            notification.email_status = Notification.EmailStatus.SKIPPED
            notification.save(update_fields=['email_status', 'updated_at'])
        return Notification.EmailStatus.SKIPPED

    if not getattr(settings, 'EMAIL_ENABLED', False):
        logger.info(
            'EMAIL_ENABLED is false; skipping send for notification %s',
            notification_id,
        )
        notification.email_status = Notification.EmailStatus.SKIPPED
        notification.save(update_fields=['email_status', 'updated_at'])
        return Notification.EmailStatus.SKIPPED

    user = notification.recipient.user
    recipient_name = (user.get_full_name() or '').strip()
    context = build_notification_email_context(
        school=notification.school,
        title=notification.title,
        body=notification.body,
        cta_path=notification.href or '/dashboard',
        cta_label=CTA_LABELS.get(notification.event_type, 'Open in app'),
        recipient_name=recipient_name,
        preheader=notification.body,
    )

    try:
        text_body = render_to_string('notifications/email/notification.txt', context)
        html_body = render_to_string('notifications/email/notification.html', context)
        message = EmailMultiAlternatives(
            subject=f'{notification.school.name}: {notification.title}',
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        message.attach_alternative(html_body, 'text/html')
        message.send(fail_silently=False)
    except Exception:
        logger.exception('Failed to send notification email %s', notification_id)
        notification.email_status = Notification.EmailStatus.FAILED
        notification.save(update_fields=['email_status', 'updated_at'])
        try:
            from notifications.services.platform_outbound import record_staff_email

            record_staff_email(
                notification=notification,
                email=email,
                ok=False,
                error_message='send_failed',
            )
        except Exception:
            logger.exception('Failed to record platform staff email failure')
        return Notification.EmailStatus.FAILED

    notification.email_status = Notification.EmailStatus.SENT
    notification.save(update_fields=['email_status', 'updated_at'])
    try:
        from notifications.services.platform_outbound import record_staff_email

        record_staff_email(notification=notification, email=email, ok=True)
    except Exception:
        logger.exception('Failed to record platform staff email delivery')
    return Notification.EmailStatus.SENT
