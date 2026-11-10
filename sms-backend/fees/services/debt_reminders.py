"""Manual guardian debt reminders from the fees desk."""

from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError

from fees.services.desk import FEE_DESK_ALL_TIME, resolve_fee_desk_term
from fees.services.fees import get_student_term_balance
from fees.services.payments import (
    format_outstanding_terms_summary,
    get_student_all_time_balance,
    list_student_outstanding_term_balances,
)
from notifications.models import GuardianDelivery
from notifications.services import guardians as guardian_services
from notifications.services.outbound import enqueue_guardian_outbound
from schools.services.settings import get_school_settings
from students.models import Student


def _unique_student_ids(student_ids) -> list:
    seen = set()
    ordered = []
    for raw in student_ids:
        key = str(raw)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(raw)
    return ordered


def _is_all_time_term(term_id) -> bool:
    return str(term_id or '').strip().lower() == FEE_DESK_ALL_TIME


def _student_balance_context(*, school, student, all_time: bool, term):
    if all_time:
        all_time_balance = get_student_all_time_balance(student=student)['balance']
        outstanding_terms = list_student_outstanding_term_balances(
            school=school,
            student=student,
        )
        return {
            'balance': all_time_balance,
            'outstanding_terms': outstanding_terms,
            'terms_summary': format_outstanding_terms_summary(outstanding_terms),
        }
    balance = get_student_term_balance(student=student, term=term)['balance']
    return {
        'balance': balance,
        'outstanding_terms': [],
        'terms_summary': '',
    }


def _sample_messages(
    *,
    school,
    student_name,
    balance,
    all_time,
    term_label,
    terms_summary,
):
    from notifications.services.message_templates import compose_email, compose_sms

    amount = f'{balance:.2f}'
    summary = terms_summary or 'multiple terms'
    ctx = {
        'school_name': school.name,
        'student_name': student_name,
        'balance': amount,
        'term_label': term_label,
        'terms_summary': summary,
        'all_time': all_time,
        'greeting': '',
    }
    sms = compose_sms(
        school=school,
        event_type=GuardianDelivery.EventType.DEBT_REMINDER,
        all_time=all_time,
        context=ctx,
    )
    subject, email_body, _html = compose_email(
        school=school,
        event_type=GuardianDelivery.EventType.DEBT_REMINDER,
        context=ctx,
    )
    return {
        'sample_sms': sms,
        'sample_email_subject': subject,
        'sample_email_body': email_body,
    }


def preview_debt_reminders(*, school, term_id, student_ids) -> dict:
    """Validate selection and estimate SMS/email attempts without sending."""
    student_ids = _unique_student_ids(student_ids)
    if not student_ids:
        raise ValidationError({'student_ids': 'Select at least one student.'})

    all_time = _is_all_time_term(term_id)
    term = None if all_time else resolve_fee_desk_term(school, term_id)
    preferences = get_school_settings(school)
    policy = guardian_services._event_policy(
        preferences,
        GuardianDelivery.EventType.DEBT_REMINDER,
    )
    enabled = bool(policy and policy.enabled)

    students = {
        str(student.id): student
        for student in Student.objects.filter(school=school, id__in=student_ids)
    }

    eligible = []
    skipped = []
    sms_count = 0
    email_count = 0
    sample = {
        'sample_sms': '',
        'sample_email_subject': '',
        'sample_email_body': '',
    }

    term_label = 'All time' if all_time else (
        f'{term.academic_year.academic_year} · {term.get_term_display()}'
    )

    for raw_id in student_ids:
        key = str(raw_id)
        student = students.get(key)
        if student is None:
            skipped.append({
                'student_id': key,
                'reason': 'Student not found in this school.',
            })
            continue

        context = _student_balance_context(
            school=school,
            student=student,
            all_time=all_time,
            term=term,
        )
        balance = context['balance']
        if balance <= 0:
            skipped.append({
                'student_id': key,
                'full_name': guardian_services._student_display_name(student),
                'reason': (
                    'No outstanding balance across terms.'
                    if all_time
                    else 'No outstanding balance for this term.'
                ),
            })
            continue

        parent_plans = []
        if enabled and policy is not None:
            links = guardian_services._resolve_guardian_links(
                student=student,
                audience=preferences.guardian_audience,
            )
            for link in links:
                channels = guardian_services.resolve_channels(
                    school_channels=policy.school_channels,
                    parent=link.parent,
                )
                parent_plans.append({
                    'parent_id': str(link.parent_id),
                    'parent_name': link.parent.name,
                    'channels': sorted(channels),
                })
                if guardian_services.CHANNEL_SMS in channels:
                    sms_count += 1
                if guardian_services.CHANNEL_EMAIL in channels:
                    email_count += 1

        if enabled and not any(plan['channels'] for plan in parent_plans):
            skipped.append({
                'student_id': key,
                'full_name': guardian_services._student_display_name(student),
                'balance': str(balance),
                'reason': 'No guardian contact matches allowed channels.',
            })
            continue

        full_name = guardian_services._student_display_name(student)
        if not sample['sample_sms']:
            sample = _sample_messages(
                school=school,
                student_name=full_name,
                balance=balance,
                all_time=all_time,
                term_label=term_label,
                terms_summary=context['terms_summary'],
            )

        eligible.append({
            'student_id': key,
            'full_name': full_name,
            'student_code': student.student_id,
            'balance': str(balance),
            'terms_summary': context['terms_summary'] or None,
            'guardians': parent_plans,
        })

    return {
        'enabled': enabled,
        'audience': preferences.guardian_audience,
        'channels': policy.school_channels if policy else None,
        'all_time': all_time,
        'term_id': FEE_DESK_ALL_TIME if all_time else term.id,
        'term_label': term_label,
        'requested_count': len(student_ids),
        'eligible_count': len(eligible),
        'skipped_count': len(skipped),
        'sms_count': sms_count if enabled else 0,
        'email_count': email_count if enabled else 0,
        'batch_size': 100,
        'eligible_ids': [row['student_id'] for row in eligible],
        'eligible': eligible[:25],
        'skipped': skipped[:25],
        'eligible_truncated': len(eligible) > 25,
        'skipped_truncated': len(skipped) > 25,
        **sample,
    }


def send_debt_reminders(*, school, term_id, student_ids) -> dict:
    """Queue debt reminders for the selected students (Celery). Returns queue summary."""
    preview = preview_debt_reminders(
        school=school,
        term_id=term_id,
        student_ids=student_ids,
    )
    if not preview['enabled']:
        raise ValidationError({
            'detail': (
                'Debt reminders are turned off. Enable them under '
                'Settings → Parent messages.'
            ),
        })
    if preview['eligible_count'] == 0:
        raise ValidationError({
            'detail': 'No eligible students to remind with the current selection.',
        })

    all_time = preview['all_time']
    term = None if all_time else resolve_fee_desk_term(school, term_id)
    batch_id = uuid.uuid4()
    students = {
        str(student.id): student
        for student in Student.objects.filter(
            school=school,
            id__in=preview['eligible_ids'],
        ).select_related('school')
    }

    sms_items: list[dict] = []
    email_items: list[dict] = []
    students_queued = 0
    for student_id in preview['eligible_ids']:
        student = students.get(str(student_id))
        if student is None:
            continue
        context = _student_balance_context(
            school=school,
            student=student,
            all_time=all_time,
            term=term,
        )
        if context['balance'] <= 0:
            continue
        planned_sms, planned_email = guardian_services.plan_guardians_debt_reminder(
            student=student,
            term=term,
            balance=context['balance'],
            batch_id=batch_id,
            all_time=all_time,
            terms_owed=[
                {
                    'term_label': row['term_label'],
                    'balance': f"{row['balance']:.2f}",
                }
                for row in context['outstanding_terms']
            ],
            terms_summary=context['terms_summary'],
        )
        if planned_sms or planned_email:
            students_queued += 1
        sms_items.extend(planned_sms)
        email_items.extend(planned_email)

    queued = enqueue_guardian_outbound(sms_items=sms_items, email_items=email_items)

    return {
        'batch_id': str(batch_id),
        'all_time': all_time,
        'term_id': FEE_DESK_ALL_TIME if all_time else term.id,
        'term_label': preview['term_label'],
        'queued': True,
        'students_notified': students_queued,
        'sms_sent': queued['sms'],
        'email_sent': queued['email'],
        'skipped_count': preview['skipped_count'],
    }
