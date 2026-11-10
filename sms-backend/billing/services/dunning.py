from __future__ import annotations

from datetime import timedelta

from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from billing.models import SchoolSubscription
from platform_admin.services.audit import record_audit
from schools.models import School


def _school_admin_emails(school: School) -> list[str]:
    emails: list[str] = []
    if school.email:
        emails.append(school.email.strip())
    from accounts.models import SchoolMembership, User

    memberships = (
        SchoolMembership.objects.filter(
            school=school,
            is_active=True,
            role=User.RoleChoices.ADMIN,
        )
        .select_related('user')
        .only('user__email')
    )
    for membership in memberships:
        email = (membership.user.email or '').strip()
        if email and email not in emails:
            emails.append(email)
    return emails


def _send_dunning_email(*, school: School, subject: str, body: str) -> int:
    recipients = _school_admin_emails(school)
    if not recipients:
        return 0
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'noreply@schoolasst.local'
    try:
        return send_mail(subject, body, from_email, recipients, fail_silently=True)
    except Exception:
        return 0


@transaction.atomic
def reactivate_subscription_after_payment(
    *,
    subscription: SchoolSubscription,
    actor=None,
    ip_address: str | None = None,
) -> SchoolSubscription:
    """Clear past-due/suspended billing state after a successful invoice payment."""
    subscription = SchoolSubscription.objects.select_for_update().select_related('school').get(
        pk=subscription.pk,
    )
    school = subscription.school
    was_locked = subscription.billing_suspended_school
    fields = ['updated_at']
    if subscription.status != SchoolSubscription.Status.ACTIVE:
        subscription.status = SchoolSubscription.Status.ACTIVE
        fields.append('status')
    if subscription.grace_period_ends_at is not None:
        subscription.grace_period_ends_at = None
        fields.append('grace_period_ends_at')
    if subscription.dunning_notice_sent_at is not None:
        subscription.dunning_notice_sent_at = None
        fields.append('dunning_notice_sent_at')
    if subscription.billing_suspended_school:
        subscription.billing_suspended_school = False
        fields.append('billing_suspended_school')
    subscription.save(update_fields=fields)

    if was_locked and school.status == School.Status.SUSPENDED:
        school.status = School.Status.ACTIVE
        school.suspended_at = None
        school.activated_at = school.activated_at or timezone.now()
        school.save(update_fields=['status', 'suspended_at', 'activated_at', 'updated_at'])
        record_audit(
            actor=actor,
            action='billing.dunning.school_reactivated',
            target_type='school',
            target_id=str(school.pk),
            detail={'subscription_id': str(subscription.pk)},
            ip_address=ip_address,
        )
    return subscription


@transaction.atomic
def suspend_for_nonpayment(
    *,
    subscription: SchoolSubscription,
    lock_school: bool = False,
) -> SchoolSubscription:
    """Mark subscription suspended after grace.

    By default the school app stays accessible so admins can open Billing and
    pay. Pass ``lock_school=True`` (or use platform school suspend) to also
    flip school lifecycle to suspended.
    """
    subscription = SchoolSubscription.objects.select_for_update().select_related('school').get(
        pk=subscription.pk,
    )
    school = subscription.school
    subscription.status = SchoolSubscription.Status.SUSPENDED
    subscription.grace_period_ends_at = subscription.grace_period_ends_at or timezone.now()
    update_fields = ['status', 'grace_period_ends_at', 'updated_at']

    if lock_school and school.status == School.Status.ACTIVE:
        school.status = School.Status.SUSPENDED
        school.suspended_at = timezone.now()
        school.save(update_fields=['status', 'suspended_at', 'updated_at'])
        subscription.billing_suspended_school = True
        update_fields.append('billing_suspended_school')

    subscription.save(update_fields=update_fields)
    record_audit(
        actor=None,
        action='billing.dunning.suspended',
        target_type='school',
        target_id=str(school.pk),
        detail={
            'subscription_id': str(subscription.pk),
            'school_locked': subscription.billing_suspended_school,
        },
    )
    _send_dunning_email(
        school=school,
        subject=f'{school.name}: subscription suspended',
        body=(
            f'Your SCHOOLASST subscription for {school.name} has been suspended '
            f'because payment was not received during the grace period.\n\n'
            f'Sign in to Billing to pay open invoices and restore access.'
        ),
    )
    return subscription


@transaction.atomic
def send_grace_reminder(*, subscription: SchoolSubscription) -> bool:
    subscription = SchoolSubscription.objects.select_for_update().select_related('school').get(
        pk=subscription.pk,
    )
    if subscription.status != SchoolSubscription.Status.PAST_DUE:
        return False
    if subscription.dunning_notice_sent_at is not None:
        return False
    grace_end = subscription.grace_period_ends_at
    if grace_end is None:
        return False

    school = subscription.school
    subscription.dunning_notice_sent_at = timezone.now()
    subscription.save(update_fields=['dunning_notice_sent_at', 'updated_at'])
    record_audit(
        actor=None,
        action='billing.dunning.grace_reminder',
        target_type='school',
        target_id=str(school.pk),
        detail={
            'subscription_id': str(subscription.pk),
            'grace_period_ends_at': grace_end.isoformat(),
        },
    )
    _send_dunning_email(
        school=school,
        subject=f'{school.name}: subscription payment due',
        body=(
            f'Your SCHOOLASST subscription for {school.name} is past due.\n\n'
            f'Grace period ends on {grace_end.date().isoformat()}. '
            f'Pay open invoices in Billing to avoid suspension.'
        ),
    )
    return True


def run_dunning_cycle(*, notice_days_before: int = 2) -> dict:
    """Daily dunning: grace reminders, then suspend after grace expires."""
    now = timezone.now()
    reminded = 0
    suspended = 0

    notice_cutoff = now + timedelta(days=notice_days_before)
    past_due = (
        SchoolSubscription.objects.filter(
            is_current=True,
            status=SchoolSubscription.Status.PAST_DUE,
            grace_period_ends_at__isnull=False,
        )
        .select_related('school')
        .order_by('grace_period_ends_at')
    )

    for subscription in past_due:
        grace_end = subscription.grace_period_ends_at
        if grace_end is None:
            continue
        if grace_end <= now:
            suspend_for_nonpayment(subscription=subscription)
            suspended += 1
            continue
        if (
            subscription.dunning_notice_sent_at is None
            and grace_end <= notice_cutoff
        ):
            if send_grace_reminder(subscription=subscription):
                reminded += 1

    return {
        'reminded': reminded,
        'suspended': suspended,
        'checked_at': now.isoformat(),
    }
