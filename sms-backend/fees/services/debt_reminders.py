"""Manual guardian debt reminders from the fees desk."""

from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError

from fees.services.desk import resolve_fee_desk_term
from fees.services.fees import get_student_term_balance
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


def preview_debt_reminders(*, school, term_id, student_ids) -> dict:
    """Validate selection and estimate SMS/email attempts without sending."""
    student_ids = _unique_student_ids(student_ids)
    if not student_ids:
        raise ValidationError({'student_ids': 'Select at least one student.'})

    term = resolve_fee_desk_term(school, term_id)
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

    for raw_id in student_ids:
        key = str(raw_id)
        student = students.get(key)
        if student is None:
            skipped.append({
                'student_id': key,
                'reason': 'Student not found in this school.',
            })
            continue

        balance = get_student_term_balance(student=student, term=term)['balance']
        if balance <= 0:
            skipped.append({
                'student_id': key,
                'full_name': guardian_services._student_display_name(student),
                'reason': 'No outstanding balance for this term.',
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

        eligible.append({
            'student_id': key,
            'full_name': guardian_services._student_display_name(student),
            'student_code': student.student_id,
            'balance': str(balance),
            'guardians': parent_plans,
        })

    return {
        'enabled': enabled,
        'audience': preferences.guardian_audience,
        'channels': policy.school_channels if policy else None,
        'term_id': term.id,
        'term_label': (
            f'{term.academic_year.academic_year} · {term.get_term_display()}'
        ),
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

    term = resolve_fee_desk_term(school, term_id)
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
        balance = get_student_term_balance(student=student, term=term)['balance']
        if balance <= 0:
            continue
        planned_sms, planned_email = guardian_services.plan_guardians_debt_reminder(
            student=student,
            term=term,
            balance=balance,
            batch_id=batch_id,
        )
        if planned_sms or planned_email:
            students_queued += 1
        sms_items.extend(planned_sms)
        email_items.extend(planned_email)

    queued = enqueue_guardian_outbound(sms_items=sms_items, email_items=email_items)

    return {
        'batch_id': str(batch_id),
        'term_id': term.id,
        'term_label': preview['term_label'],
        'queued': True,
        'students_notified': students_queued,
        'sms_sent': queued['sms'],
        'email_sent': queued['email'],
        'skipped_count': preview['skipped_count'],
    }
