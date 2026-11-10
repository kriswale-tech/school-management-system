"""Outbound SMS/email to Parent contacts (guardian communications).

Planning happens in-request; actual SMS/email go through Celery batches of 100
(Arkesel multi-recipient + Resend batch API).
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from decimal import Decimal

from notifications.models import GuardianDelivery
from notifications.services.email_context import default_app_logo_url
from notifications.services.message_templates import compose_email, compose_sms
from notifications.services.outbound import (
    enqueue_guardian_outbound,
    record_delivery_result,
)
from schools.models import SchoolSettings
from schools.services.settings import get_school_settings
from students.models import Parent, Student, StudentParent

logger = logging.getLogger(__name__)

CHANNEL_SMS = GuardianDelivery.Channel.SMS
CHANNEL_EMAIL = GuardianDelivery.Channel.EMAIL


@dataclass(frozen=True)
class EventPolicy:
    enabled: bool
    school_channels: str


def _event_policy(preferences: SchoolSettings, event_type: str) -> EventPolicy | None:
    mapping = {
        GuardianDelivery.EventType.WARD_ENROLLED: (
            preferences.guardian_ward_enrolled_enabled,
            preferences.guardian_ward_enrolled_channels,
        ),
        GuardianDelivery.EventType.PAYMENT_RECEIPT: (
            preferences.guardian_payment_receipt_enabled,
            preferences.guardian_payment_receipt_channels,
        ),
        GuardianDelivery.EventType.DEBT_REMINDER: (
            preferences.guardian_debt_reminder_enabled,
            preferences.guardian_debt_reminder_channels,
        ),
        GuardianDelivery.EventType.REPORT_READY: (
            preferences.guardian_report_ready_enabled,
            preferences.guardian_report_ready_channels,
        ),
        GuardianDelivery.EventType.NEXT_TERM_FEES: (
            preferences.guardian_next_term_fees_enabled,
            preferences.guardian_next_term_fees_channels,
        ),
    }
    row = mapping.get(event_type)
    if row is None:
        return None
    enabled, channels = row
    return EventPolicy(enabled=enabled, school_channels=channels)


def _channel_set(value: str) -> set[str]:
    if value == Parent.NotifyChannel.OFF:
        return set()
    if value == Parent.NotifyChannel.BOTH or value == SchoolSettings.GuardianChannel.BOTH:
        return {CHANNEL_SMS, CHANNEL_EMAIL}
    if value in {CHANNEL_SMS, CHANNEL_EMAIL}:
        return {value}
    return set()


def resolve_channels(*, school_channels: str, parent: Parent) -> set[str]:
    """School allow ∩ parent prefer ∩ available contact details."""
    allowed = _channel_set(school_channels) & _channel_set(parent.notify_channel)
    resolved: set[str] = set()
    if CHANNEL_SMS in allowed and (parent.phone_number or '').strip():
        resolved.add(CHANNEL_SMS)
    if CHANNEL_EMAIL in allowed and (parent.email or '').strip():
        resolved.add(CHANNEL_EMAIL)
    return resolved


def _student_display_name(student: Student) -> str:
    return ' '.join(
        part
        for part in (student.first_name, student.other_names, student.last_name)
        if part
    ).strip()


def _resolve_guardian_links(*, student: Student, audience: str):
    links = (
        StudentParent.objects.filter(student=student)
        .select_related('parent')
        .order_by('-is_primary', 'created_at')
    )
    if audience == SchoolSettings.GuardianAudience.PRIMARY:
        primary = [link for link in links if link.is_primary]
        return primary or list(links[:1])
    return list(links)


def _idempotency_key(*, event_type: str, scope_id, parent_id, channel: str) -> str:
    """Stable ≤120-char key (CharField limit). Hash keeps long UUIDs from colliding."""
    raw = f'{event_type}:{scope_id}:{parent_id}:{channel}'
    if len(raw) <= 120:
        return raw
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    prefix = event_type[:24]
    return f'{prefix}:{digest}'[:120]


def _sms_item(*, school, parent, student, event_type, body, idempotency_key) -> dict:
    return {
        'school_id': str(school.id),
        'parent_id': str(parent.id),
        'student_id': str(student.id) if student is not None else None,
        'event_type': event_type,
        'recipient_address': parent.phone_number,
        'body': body,
        'idempotency_key': idempotency_key,
    }


def _email_item(
    *,
    school,
    parent,
    student,
    event_type,
    context,
    idempotency_key,
) -> dict:
    subject, text_body, html_body = compose_email(
        school=school,
        event_type=event_type,
        context=context,
    )
    return {
        'school_id': str(school.id),
        'parent_id': str(parent.id),
        'student_id': str(student.id) if student is not None else None,
        'event_type': event_type,
        'recipient_address': (parent.email or '').strip(),
        'subject': subject,
        'text_body': text_body,
        'html_body': html_body,
        'idempotency_key': idempotency_key,
    }


def _record_skip(*, school, parent, student, event_type, scope_id) -> None:
    record_delivery_result(
        school_id=school.id,
        parent_id=parent.id,
        student_id=student.id if student is not None else None,
        event_type=event_type,
        channel=CHANNEL_SMS,
        status=GuardianDelivery.Status.SKIPPED,
        recipient_address='',
        body_preview='',
        idempotency_key=_idempotency_key(
            event_type=event_type,
            scope_id=scope_id,
            parent_id=parent.id,
            channel='none',
        ),
        skip_reason='No matching channel or contact details',
    )


def notify_guardians_ward_enrolled(*, student: Student, class_name: str = '') -> dict:
    """Plan + enqueue ward-enrolled notices. Returns queued channel counts."""
    school = student.school
    preferences = get_school_settings(school)
    policy = _event_policy(preferences, GuardianDelivery.EventType.WARD_ENROLLED)
    if policy is None or not policy.enabled:
        return {'sms': 0, 'email': 0}

    student_name = _student_display_name(student)
    school_name = school.name
    links = _resolve_guardian_links(
        student=student,
        audience=preferences.guardian_audience,
    )
    sms_items = []
    email_items = []

    for link in links:
        parent = link.parent
        channels = resolve_channels(
            school_channels=policy.school_channels,
            parent=parent,
        )
        if not channels:
            _record_skip(
                school=school,
                parent=parent,
                student=student,
                event_type=GuardianDelivery.EventType.WARD_ENROLLED,
                scope_id=student.id,
            )
            continue

        if CHANNEL_SMS in channels:
            sms_items.append(
                _sms_item(
                    school=school,
                    parent=parent,
                    student=student,
                    event_type=GuardianDelivery.EventType.WARD_ENROLLED,
                    body=compose_sms(
                        school=school,
                        event_type=GuardianDelivery.EventType.WARD_ENROLLED,
                        context={
                            'school_name': school_name,
                            'student_name': student_name,
                            'class_part': f' ({class_name})' if class_name else '',
                        },
                    ),
                    idempotency_key=_idempotency_key(
                        event_type=GuardianDelivery.EventType.WARD_ENROLLED,
                        scope_id=student.id,
                        parent_id=parent.id,
                        channel=CHANNEL_SMS,
                    ),
                ),
            )

        if CHANNEL_EMAIL in channels:
            greeting_name = (parent.name or '').strip()
            email_items.append(
                _email_item(
                    school=school,
                    parent=parent,
                    student=student,
                    event_type=GuardianDelivery.EventType.WARD_ENROLLED,
                    context={
                        'greeting': f'Hi {greeting_name},' if greeting_name else '',
                        'school_name': school_name,
                        'student_name': student_name,
                        'class_name': class_name,
                        'class_part': f' ({class_name})' if class_name else '',
                        'app_logo_url': default_app_logo_url(),
                        'preheader': f'{student_name} has been enrolled at {school_name}',
                    },
                    idempotency_key=_idempotency_key(
                        event_type=GuardianDelivery.EventType.WARD_ENROLLED,
                        scope_id=student.id,
                        parent_id=parent.id,
                        channel=CHANNEL_EMAIL,
                    ),
                ),
            )

    return enqueue_guardian_outbound(sms_items=sms_items, email_items=email_items)


def schedule_ward_enrolled_notice(*, student_id, class_name: str = '') -> None:
    """Queue ward-enrolled planning after the surrounding transaction commits."""

    def _run():
        student = (
            Student.objects.select_related('school')
            .filter(id=student_id)
            .first()
        )
        if student is None:
            return
        notify_guardians_ward_enrolled(student=student, class_name=class_name)

    from django.db import transaction

    transaction.on_commit(_run)


def notify_guardians_payment_receipt(
    *,
    student: Student,
    payment_id,
    receipt_id,
    receipt_number: str,
    amount,
) -> dict:
    """Plan + enqueue payment receipt notices."""
    from fees.services.receipts import build_receipt_public_url

    school = student.school
    preferences = get_school_settings(school)
    policy = _event_policy(preferences, GuardianDelivery.EventType.PAYMENT_RECEIPT)
    if policy is None or not policy.enabled:
        return {'sms': 0, 'email': 0}

    student_name = _student_display_name(student)
    school_name = school.name
    receipt_url = build_receipt_public_url(receipt_id)
    links = _resolve_guardian_links(
        student=student,
        audience=preferences.guardian_audience,
    )
    sms_items = []
    email_items = []

    for link in links:
        parent = link.parent
        channels = resolve_channels(
            school_channels=policy.school_channels,
            parent=parent,
        )
        if not channels:
            _record_skip(
                school=school,
                parent=parent,
                student=student,
                event_type=GuardianDelivery.EventType.PAYMENT_RECEIPT,
                scope_id=payment_id,
            )
            continue

        if CHANNEL_SMS in channels:
            sms_items.append(
                _sms_item(
                    school=school,
                    parent=parent,
                    student=student,
                    event_type=GuardianDelivery.EventType.PAYMENT_RECEIPT,
                    body=compose_sms(
                        school=school,
                        event_type=GuardianDelivery.EventType.PAYMENT_RECEIPT,
                        context={
                            'school_name': school_name,
                            'student_name': student_name,
                            'amount': amount,
                            'receipt_number': receipt_number,
                            'receipt_url': receipt_url,
                        },
                    ),
                    idempotency_key=_idempotency_key(
                        event_type=GuardianDelivery.EventType.PAYMENT_RECEIPT,
                        scope_id=payment_id,
                        parent_id=parent.id,
                        channel=CHANNEL_SMS,
                    ),
                ),
            )

        if CHANNEL_EMAIL in channels:
            greeting_name = (parent.name or '').strip()
            email_items.append(
                _email_item(
                    school=school,
                    parent=parent,
                    student=student,
                    event_type=GuardianDelivery.EventType.PAYMENT_RECEIPT,
                    context={
                        'greeting': f'Hi {greeting_name},' if greeting_name else '',
                        'school_name': school_name,
                        'student_name': student_name,
                        'amount': amount,
                        'receipt_number': receipt_number,
                        'receipt_url': receipt_url,
                        'app_logo_url': default_app_logo_url(),
                        'preheader': f'Payment of GHS {amount} received for {student_name}',
                    },
                    idempotency_key=_idempotency_key(
                        event_type=GuardianDelivery.EventType.PAYMENT_RECEIPT,
                        scope_id=payment_id,
                        parent_id=parent.id,
                        channel=CHANNEL_EMAIL,
                    ),
                ),
            )

    return enqueue_guardian_outbound(sms_items=sms_items, email_items=email_items)


def schedule_payment_receipt_notice(
    *,
    student_id,
    payment_id,
    receipt_id,
    receipt_number: str,
    amount,
) -> None:
    """Queue payment-receipt planning after the surrounding transaction commits."""

    def _run():
        student = (
            Student.objects.select_related('school')
            .filter(id=student_id)
            .first()
        )
        if student is None:
            return
        notify_guardians_payment_receipt(
            student=student,
            payment_id=payment_id,
            receipt_id=receipt_id,
            receipt_number=receipt_number,
            amount=amount,
        )

    from django.db import transaction

    transaction.on_commit(_run)


def plan_guardians_debt_reminder(
    *,
    student: Student,
    term,
    balance,
    batch_id,
    all_time: bool = False,
    terms_owed: list[dict] | None = None,
    terms_summary: str = '',
) -> tuple[list[dict], list[dict]]:
    """Build SMS/email items for one student without sending."""
    school = student.school
    preferences = get_school_settings(school)
    policy = _event_policy(preferences, GuardianDelivery.EventType.DEBT_REMINDER)
    if policy is None or not policy.enabled:
        return [], []

    student_name = _student_display_name(student)
    school_name = school.name
    if all_time:
        term_label = 'all terms'
    else:
        term_label = f'{term.academic_year.academic_year} · {term.get_term_display()}'
    amount = balance if isinstance(balance, Decimal) else Decimal(str(balance))
    amount_display = f'{amount:.2f}'
    scope = f'{batch_id}:{student.id}'
    terms_owed = terms_owed or []
    sms_items = []
    email_items = []

    links = _resolve_guardian_links(
        student=student,
        audience=preferences.guardian_audience,
    )
    for link in links:
        parent = link.parent
        channels = resolve_channels(
            school_channels=policy.school_channels,
            parent=parent,
        )
        if not channels:
            _record_skip(
                school=school,
                parent=parent,
                student=student,
                event_type=GuardianDelivery.EventType.DEBT_REMINDER,
                scope_id=scope,
            )
            continue

        if CHANNEL_SMS in channels:
            sms_items.append(
                _sms_item(
                    school=school,
                    parent=parent,
                    student=student,
                    event_type=GuardianDelivery.EventType.DEBT_REMINDER,
                    body=compose_sms(
                        school=school,
                        event_type=GuardianDelivery.EventType.DEBT_REMINDER,
                        all_time=all_time,
                        context={
                            'school_name': school_name,
                            'student_name': student_name,
                            'balance': amount_display,
                            'term_label': term_label,
                            'terms_summary': terms_summary or 'multiple terms',
                        },
                    ),
                    idempotency_key=_idempotency_key(
                        event_type=GuardianDelivery.EventType.DEBT_REMINDER,
                        scope_id=scope,
                        parent_id=parent.id,
                        channel=CHANNEL_SMS,
                    ),
                ),
            )

        if CHANNEL_EMAIL in channels:
            greeting_name = (parent.name or '').strip()
            preheader = (
                f'{student_name} owes GHS {amount_display} across terms'
                if all_time
                else f'{student_name} has an outstanding balance of GHS {amount_display}'
            )
            email_items.append(
                _email_item(
                    school=school,
                    parent=parent,
                    student=student,
                    event_type=GuardianDelivery.EventType.DEBT_REMINDER,
                    context={
                        'greeting': f'Hi {greeting_name},' if greeting_name else '',
                        'school_name': school_name,
                        'student_name': student_name,
                        'balance': amount_display,
                        'term_label': term_label,
                        'all_time': all_time,
                        'terms_owed': terms_owed,
                        'terms_summary': terms_summary or 'multiple terms',
                        'app_logo_url': default_app_logo_url(),
                        'preheader': preheader,
                    },
                    idempotency_key=_idempotency_key(
                        event_type=GuardianDelivery.EventType.DEBT_REMINDER,
                        scope_id=scope,
                        parent_id=parent.id,
                        channel=CHANNEL_EMAIL,
                    ),
                ),
            )

    return sms_items, email_items


def notify_guardians_debt_reminder(
    *,
    student: Student,
    term,
    balance,
    batch_id,
    all_time: bool = False,
    terms_owed: list[dict] | None = None,
    terms_summary: str = '',
) -> dict:
    """Plan + enqueue debt reminder for one student."""
    sms_items, email_items = plan_guardians_debt_reminder(
        student=student,
        term=term,
        balance=balance,
        batch_id=batch_id,
        all_time=all_time,
        terms_owed=terms_owed,
        terms_summary=terms_summary,
    )
    return enqueue_guardian_outbound(sms_items=sms_items, email_items=email_items)


def plan_guardians_report_ready(
    *,
    student: Student,
    report,
    batch_id,
) -> tuple[list[dict], list[dict]]:
    """Build SMS/email items for one report without sending."""
    from assessments.services.report_links import build_report_public_url

    school = student.school
    preferences = get_school_settings(school)
    policy = _event_policy(preferences, GuardianDelivery.EventType.REPORT_READY)
    if policy is None or not policy.enabled:
        return [], []

    student_name = _student_display_name(student)
    school_name = school.name
    term = report.term
    term_label = f'{term.academic_year.academic_year} · {term.get_term_display()}'
    report_url = build_report_public_url(report.id)
    scope = f'{batch_id}:{report.id}'
    sms_items = []
    email_items = []

    links = _resolve_guardian_links(
        student=student,
        audience=preferences.guardian_audience,
    )
    for link in links:
        parent = link.parent
        channels = resolve_channels(
            school_channels=policy.school_channels,
            parent=parent,
        )
        if not channels:
            _record_skip(
                school=school,
                parent=parent,
                student=student,
                event_type=GuardianDelivery.EventType.REPORT_READY,
                scope_id=scope,
            )
            continue

        if CHANNEL_SMS in channels:
            sms_items.append(
                _sms_item(
                    school=school,
                    parent=parent,
                    student=student,
                    event_type=GuardianDelivery.EventType.REPORT_READY,
                    body=compose_sms(
                        school=school,
                        event_type=GuardianDelivery.EventType.REPORT_READY,
                        context={
                            'school_name': school_name,
                            'student_name': student_name,
                            'term_label': term_label,
                            'report_url': report_url,
                        },
                    ),
                    idempotency_key=_idempotency_key(
                        event_type=GuardianDelivery.EventType.REPORT_READY,
                        scope_id=scope,
                        parent_id=parent.id,
                        channel=CHANNEL_SMS,
                    ),
                ),
            )

        if CHANNEL_EMAIL in channels:
            greeting_name = (parent.name or '').strip()
            email_items.append(
                _email_item(
                    school=school,
                    parent=parent,
                    student=student,
                    event_type=GuardianDelivery.EventType.REPORT_READY,
                    context={
                        'greeting': f'Hi {greeting_name},' if greeting_name else '',
                        'school_name': school_name,
                        'student_name': student_name,
                        'term_label': term_label,
                        'report_url': report_url,
                        'app_logo_url': default_app_logo_url(),
                        'preheader': f'{student_name}\'s report is ready',
                    },
                    idempotency_key=_idempotency_key(
                        event_type=GuardianDelivery.EventType.REPORT_READY,
                        scope_id=scope,
                        parent_id=parent.id,
                        channel=CHANNEL_EMAIL,
                    ),
                ),
            )

    return sms_items, email_items


def notify_guardians_report_ready(
    *,
    student: Student,
    report,
    batch_id,
) -> dict:
    """Plan + enqueue report-ready notices for one student."""
    sms_items, email_items = plan_guardians_report_ready(
        student=student,
        report=report,
        batch_id=batch_id,
    )
    return enqueue_guardian_outbound(sms_items=sms_items, email_items=email_items)


def plan_guardians_next_term_fees(
    *,
    student: Student,
    term,
    fee_structure,
) -> tuple[list[dict], list[dict]]:
    """Build SMS/email items for one student's applied fee schedule."""
    from fees.models import StudentFee
    from fees.services.fee_schedule_links import build_fee_schedule_public_url

    school = student.school
    preferences = get_school_settings(school)
    policy = _event_policy(preferences, GuardianDelivery.EventType.NEXT_TERM_FEES)
    if policy is None or not policy.enabled:
        return [], []

    fees = list(
        StudentFee.objects.filter(
            student=student,
            term=term,
            fee_structure=fee_structure,
        ).order_by('name'),
    )
    if not fees:
        return [], []

    student_name = _student_display_name(student)
    school_name = school.name
    term_label = f'{term.academic_year.academic_year} · {term.get_term_display()}'
    total = sum((fee.amount for fee in fees), Decimal('0.00'))
    total_display = f'{total:.2f}'
    schedule_url = build_fee_schedule_public_url(
        student_id=student.id,
        term_id=term.id,
    )
    # One notice per student/term — safe across apply + late-enrollment hooks.
    scope = f'{term.id}:{student.id}'
    sms_items = []
    email_items = []
    item_rows = [
        {'name': fee.name, 'amount': f'{fee.amount:.2f}'}
        for fee in fees
    ]

    links = _resolve_guardian_links(
        student=student,
        audience=preferences.guardian_audience,
    )
    for link in links:
        parent = link.parent
        channels = resolve_channels(
            school_channels=policy.school_channels,
            parent=parent,
        )
        if not channels:
            _record_skip(
                school=school,
                parent=parent,
                student=student,
                event_type=GuardianDelivery.EventType.NEXT_TERM_FEES,
                scope_id=scope,
            )
            continue

        if CHANNEL_SMS in channels:
            sms_items.append(
                _sms_item(
                    school=school,
                    parent=parent,
                    student=student,
                    event_type=GuardianDelivery.EventType.NEXT_TERM_FEES,
                    body=compose_sms(
                        school=school,
                        event_type=GuardianDelivery.EventType.NEXT_TERM_FEES,
                        context={
                            'school_name': school_name,
                            'student_name': student_name,
                            'term_label': term_label,
                            'total_display': total_display,
                            'schedule_url': schedule_url,
                        },
                    ),
                    idempotency_key=_idempotency_key(
                        event_type=GuardianDelivery.EventType.NEXT_TERM_FEES,
                        scope_id=scope,
                        parent_id=parent.id,
                        channel=CHANNEL_SMS,
                    ),
                ),
            )

        if CHANNEL_EMAIL in channels:
            greeting_name = (parent.name or '').strip()
            email_items.append(
                _email_item(
                    school=school,
                    parent=parent,
                    student=student,
                    event_type=GuardianDelivery.EventType.NEXT_TERM_FEES,
                    context={
                        'greeting': f'Hi {greeting_name},' if greeting_name else '',
                        'school_name': school_name,
                        'student_name': student_name,
                        'term_label': term_label,
                        'total': total_display,
                        'total_display': total_display,
                        'items': item_rows,
                        'schedule_url': schedule_url,
                        'app_logo_url': default_app_logo_url(),
                        'preheader': (
                            f'Fees for {student_name} total GHS {total_display}'
                        ),
                    },
                    idempotency_key=_idempotency_key(
                        event_type=GuardianDelivery.EventType.NEXT_TERM_FEES,
                        scope_id=scope,
                        parent_id=parent.id,
                        channel=CHANNEL_EMAIL,
                    ),
                ),
            )

    return sms_items, email_items


def notify_guardians_next_term_fees(
    *,
    student: Student,
    term,
    fee_structure,
) -> dict:
    """Plan + enqueue next-term fee notices for one student."""
    sms_items, email_items = plan_guardians_next_term_fees(
        student=student,
        term=term,
        fee_structure=fee_structure,
    )
    return enqueue_guardian_outbound(sms_items=sms_items, email_items=email_items)
