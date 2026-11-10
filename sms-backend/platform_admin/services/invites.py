from __future__ import annotations

import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from accounts.models import Profile, SchoolMembership, User
from accounts.services.memberships import link_user_to_school
from platform_admin.models import PlatformUser, SchoolAdminInvite
from platform_admin.services.audit import record_audit
from schools.models import School

logger = logging.getLogger(__name__)

INVITE_TTL_DAYS = 14


def _invite_expiry():
    return timezone.now() + timedelta(days=INVITE_TTL_DAYS)


def invite_accept_url(token: str) -> str:
    base = getattr(settings, 'FRONTEND_URL', 'http://localhost:3003').rstrip('/')
    return f'{base}/auth/invite/{token}'


def get_invite_by_token(token: str) -> SchoolAdminInvite:
    invite = (
        SchoolAdminInvite.objects.select_related('school', 'created_by')
        .filter(token=token)
        .first()
    )
    if invite is None:
        raise NotFound('Invite not found.')
    return invite


def refresh_expired_invite(invite: SchoolAdminInvite) -> SchoolAdminInvite:
    if (
        invite.status == SchoolAdminInvite.Status.PENDING
        and invite.expires_at <= timezone.now()
    ):
        invite.status = SchoolAdminInvite.Status.EXPIRED
        invite.save(update_fields=['status', 'updated_at'])
    return invite


def _send_invite_email(invite: SchoolAdminInvite) -> None:
    url = invite_accept_url(invite.token)
    subject = f'You are invited to administer {invite.school.name} on SCHOOLASST'
    body = (
        f'Hello {invite.first_name},\n\n'
        f'You have been invited to set up and administer {invite.school.name} '
        f'on SCHOOLASST.\n\n'
        f'Accept your invitation:\n{url}\n\n'
        f'This link expires on {invite.expires_at:%Y-%m-%d %H:%M %Z}.\n'
    )
    if getattr(settings, 'EMAIL_ENABLED', False) and invite.email:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invite.email],
            fail_silently=True,
        )
    else:
        logger.info('School admin invite for %s: %s', invite.phone_number, url)


@transaction.atomic
def create_admin_invite(
    *,
    actor: PlatformUser,
    school: School,
    phone_number: str,
    email: str,
    first_name: str,
    last_name: str = '',
    ip_address: str | None = None,
) -> SchoolAdminInvite:
    phone = phone_number.strip()
    existing_pending = SchoolAdminInvite.objects.filter(
        school=school,
        phone_number=phone,
        status=SchoolAdminInvite.Status.PENDING,
        expires_at__gt=timezone.now(),
    ).exists()
    if existing_pending:
        raise ValidationError({
            'phone_number': 'A pending invite already exists for this phone number.',
        })

    already_admin = SchoolMembership.objects.filter(
        school=school,
        user__phone_number=phone,
        role=User.RoleChoices.ADMIN,
        is_active=True,
    ).exists()
    if already_admin:
        raise ValidationError({
            'phone_number': 'This person is already an admin of this school.',
        })

    invite = SchoolAdminInvite.objects.create(
        school=school,
        phone_number=phone,
        email=email.strip().lower(),
        first_name=first_name.strip(),
        last_name=(last_name or '').strip(),
        token=secrets.token_urlsafe(32),
        expires_at=_invite_expiry(),
        created_by=actor,
        status=SchoolAdminInvite.Status.PENDING,
    )
    _send_invite_email(invite)
    record_audit(
        actor=actor,
        action='platform.school.invite_sent',
        target_type='school',
        target_id=str(school.pk),
        detail={
            'invite_id': str(invite.pk),
            'phone_number': invite.phone_number,
            'email': invite.email,
        },
        ip_address=ip_address,
    )
    return invite


@transaction.atomic
def resend_admin_invite(
    *,
    actor: PlatformUser,
    invite: SchoolAdminInvite,
    ip_address: str | None = None,
) -> SchoolAdminInvite:
    invite = refresh_expired_invite(invite)
    if invite.status not in {
        SchoolAdminInvite.Status.PENDING,
        SchoolAdminInvite.Status.EXPIRED,
    }:
        raise ValidationError({'detail': 'Only pending or expired invites can be resent.'})

    invite.token = secrets.token_urlsafe(32)
    invite.expires_at = _invite_expiry()
    invite.status = SchoolAdminInvite.Status.PENDING
    invite.save(update_fields=['token', 'expires_at', 'status', 'updated_at'])
    _send_invite_email(invite)
    record_audit(
        actor=actor,
        action='platform.school.invite_resent',
        target_type='school',
        target_id=str(invite.school_id),
        detail={'invite_id': str(invite.pk)},
        ip_address=ip_address,
    )
    return invite


@transaction.atomic
def accept_admin_invite(*, token: str) -> dict:
    invite = refresh_expired_invite(get_invite_by_token(token))
    if invite.status != SchoolAdminInvite.Status.PENDING:
        raise ValidationError({'detail': 'This invite is no longer valid.'})
    if invite.expires_at <= timezone.now():
        invite.status = SchoolAdminInvite.Status.EXPIRED
        invite.save(update_fields=['status', 'updated_at'])
        raise ValidationError({'detail': 'This invite has expired.'})

    school = invite.school
    user = User.objects.filter(phone_number=invite.phone_number).first()
    created_user = False
    if user is None:
        user = User.objects.create(
            phone_number=invite.phone_number,
            email=invite.email,
            first_name=invite.first_name,
            last_name=invite.last_name,
            is_active=True,
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])
        Profile.objects.get_or_create(user=user)
        created_user = True
    else:
        updates = []
        if invite.email and user.email != invite.email:
            user.email = invite.email
            updates.append('email')
        if invite.first_name and not user.first_name:
            user.first_name = invite.first_name
            updates.append('first_name')
        if invite.last_name and not user.last_name:
            user.last_name = invite.last_name
            updates.append('last_name')
        if not user.is_active:
            user.is_active = True
            updates.append('is_active')
        if updates:
            user.save(update_fields=[*updates, 'updated_at'])

    membership, _ = link_user_to_school(user, school, User.RoleChoices.ADMIN)

    invite.status = SchoolAdminInvite.Status.ACCEPTED
    invite.accepted_at = timezone.now()
    invite.accepted_user = user
    invite.save(
        update_fields=['status', 'accepted_at', 'accepted_user', 'updated_at'],
    )

    if school.status == School.Status.PENDING:
        # Activate without a platform actor — attribute to system in audit.
        previous = school.status
        school.status = School.Status.ACTIVE
        school.activated_at = school.activated_at or timezone.now()
        school.suspended_at = None
        school.save(
            update_fields=['status', 'activated_at', 'suspended_at', 'updated_at'],
        )
        record_audit(
            actor=None,
            action='platform.school.status_changed',
            target_type='school',
            target_id=str(school.pk),
            detail={
                'from': previous,
                'to': School.Status.ACTIVE,
                'reason': 'admin_invite_accepted',
                'invite_id': str(invite.pk),
            },
        )

    record_audit(
        actor=None,
        action='platform.school.invite_accepted',
        target_type='school',
        target_id=str(school.pk),
        detail={
            'invite_id': str(invite.pk),
            'user_id': str(user.pk),
            'created_user': created_user,
        },
    )

    return {
        'invite': invite,
        'user': user,
        'membership': membership,
        'school': school,
        'created_user': created_user,
    }
