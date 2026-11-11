"""Manual (and auto) guardian report-ready notices."""

from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError

from assessments.models import Report, StudentResult
from communications.services.coverage import credit_coverage_for_send
from assessments.services.admin_overview import _load_stream
from assessments.services.report_pdf import _report_file_exists
from notifications.models import GuardianDelivery
from notifications.services import guardians as guardian_services
from notifications.services.outbound import enqueue_guardian_outbound
from schools.models import SchoolSettings
from schools.services.settings import get_school_settings
from students.services import resolve_term


def _unique_ids(values) -> list:
    seen = set()
    ordered = []
    for raw in values:
        key = str(raw)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(raw)
    return ordered


def preview_report_ready_notices(*, school, stream_id, term_id, student_ids) -> dict:
    student_ids = _unique_ids(student_ids)
    if not student_ids:
        raise ValidationError({'student_ids': 'Select at least one student.'})

    term = resolve_term(school, term_id)
    stream = _load_stream(school=school, stream_id=stream_id)
    preferences = get_school_settings(school)
    policy = guardian_services._event_policy(
        preferences,
        GuardianDelivery.EventType.REPORT_READY,
    )
    enabled = bool(policy and policy.enabled)

    reports = {
        str(report.student_id): report
        for report in Report.objects.filter(
            school=school,
            stream_id=stream.id,
            term_id=term.id,
            student_id__in=student_ids,
        ).select_related('student')
    }
    released_ids = set(
        str(student_id)
        for student_id in StudentResult.objects.filter(
            term_id=term.id,
            stream_id=stream.id,
            status=StudentResult.Status.RELEASED,
            student_id__in=student_ids,
        ).values_list('student_id', flat=True)
    )
    # Also allow stream-null result rows used historically.
    released_ids.update(
        str(student_id)
        for student_id in StudentResult.objects.filter(
            term_id=term.id,
            class_level_id=stream.class_level_id,
            stream__isnull=True,
            status=StudentResult.Status.RELEASED,
            student_id__in=student_ids,
        ).values_list('student_id', flat=True)
    )

    eligible = []
    skipped = []
    sms_count = 0
    email_count = 0

    for raw_id in student_ids:
        key = str(raw_id)
        report = reports.get(key)
        if key not in released_ids:
            skipped.append({
                'student_id': key,
                'reason': 'Results are not released for this student.',
            })
            continue
        if report is None or not _report_file_exists(report):
            skipped.append({
                'student_id': key,
                'full_name': (
                    guardian_services._student_display_name(report.student)
                    if report is not None
                    else ''
                ),
                'reason': 'Report PDF has not been generated yet.',
            })
            continue

        student = report.student
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
                'reason': 'No guardian contact matches allowed channels.',
            })
            continue

        eligible.append({
            'student_id': key,
            'report_id': str(report.id),
            'full_name': guardian_services._student_display_name(student),
            'student_code': student.student_id,
            'guardians': parent_plans,
        })

    return {
        'enabled': enabled,
        'notify_mode': preferences.report_parent_notify_mode,
        'audience': preferences.guardian_audience,
        'channels': policy.school_channels if policy else None,
        'term_id': term.id,
        'term_label': f'{term.academic_year.academic_year} · {term.get_term_display()}',
        'stream_id': stream.id,
        'class_name': stream.full_name,
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
        'credits': credit_coverage_for_send(
            school=school,
            sms_count=sms_count if enabled else 0,
            email_count=email_count if enabled else 0,
        ),
    }


def send_report_ready_notices(*, school, stream_id, term_id, student_ids) -> dict:
    preview = preview_report_ready_notices(
        school=school,
        stream_id=stream_id,
        term_id=term_id,
        student_ids=student_ids,
    )
    if not preview['enabled']:
        raise ValidationError({
            'detail': (
                'Report-ready messages are turned off. Enable them under '
                'Settings → Parent messages.'
            ),
        })
    if preview['eligible_count'] == 0:
        raise ValidationError({
            'detail': 'No eligible students to notify with the current selection.',
        })

    term = resolve_term(school, term_id)
    stream = _load_stream(school=school, stream_id=stream_id)
    batch_id = uuid.uuid4()
    reports = {
        str(report.student_id): report
        for report in Report.objects.filter(
            school=school,
            stream_id=stream.id,
            term_id=term.id,
            student_id__in=preview['eligible_ids'],
        ).select_related('student', 'school', 'term', 'term__academic_year', 'stream')
    }

    sms_items: list[dict] = []
    email_items: list[dict] = []
    students_queued = 0
    for student_id in preview['eligible_ids']:
        report = reports.get(str(student_id))
        if report is None or not _report_file_exists(report):
            continue
        planned_sms, planned_email = guardian_services.plan_guardians_report_ready(
            student=report.student,
            report=report,
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
        'stream_id': stream.id,
        'class_name': stream.full_name,
        'queued': True,
        'students_notified': students_queued,
        'sms_sent': queued['sms'],
        'email_sent': queued['email'],
        'skipped_count': preview['skipped_count'],
    }


def maybe_auto_notify_report_ready(*, report: Report) -> None:
    """If settings say auto + enabled, enqueue notify after a report PDF is generated.

    Idempotency is scoped to ``report.id`` + ``generation_id`` so parents get one
    auto notice per PDF generation. Regenerating (new generation_id) allows another
    auto send; skipping an existing file does not bump generation_id.
    """
    preferences = get_school_settings(report.school)
    if preferences.report_parent_notify_mode != SchoolSettings.ReportParentNotifyMode.AUTO:
        return
    if not preferences.guardian_report_ready_enabled:
        return
    if not _report_file_exists(report):
        return
    generation = report.generation_id or report.generated_at or 'none'
    guardian_services.notify_guardians_report_ready(
        student=report.student,
        report=report,
        batch_id=f'auto-{report.id}-{generation}',
    )
