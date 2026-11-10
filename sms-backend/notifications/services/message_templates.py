"""School-scoped guardian message templates + preview/SMS analysis."""

from __future__ import annotations

import html
import re
from typing import Any

from django.conf import settings
from django.template.loader import render_to_string
from rest_framework.exceptions import ValidationError

from communications.services.segments import analyze_sms
from notifications.models import GuardianDelivery, GuardianMessageTemplate

PLACEHOLDER_RE = re.compile(r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}')

# Defaults are the editable SMS body AFTER the fixed sender prefix.
DEFAULT_SMS: dict[str, str] = {
    GuardianDelivery.EventType.WARD_ENROLLED: (
        '{{student_name}} has been enrolled{{class_part}}. You are listed as a guardian.'
    ),
    GuardianDelivery.EventType.PAYMENT_RECEIPT: (
        'Payment of GHS {{amount}} received for {{student_name}}. '
        'Receipt {{receipt_number}}: {{receipt_url}}'
    ),
    GuardianDelivery.EventType.DEBT_REMINDER: (
        'Reminder — {{student_name}} has an outstanding balance of GHS {{balance}} '
        'for {{term_label}}. Please contact the school to pay.'
    ),
    GuardianDelivery.EventType.REPORT_READY: (
        "{{student_name}}'s report for {{term_label}} is ready. Download: {{report_url}}"
    ),
    GuardianDelivery.EventType.NEXT_TERM_FEES: (
        'Fees for {{student_name}} ({{term_label}}) total GHS {{total_display}}. '
        'Details: {{schedule_url}}'
    ),
}

DEFAULT_SMS_ALL_TIME = (
    'Reminder — {{student_name}} owes GHS {{balance}} across terms '
    '({{terms_summary}}). Please contact the school to pay.'
)

DEFAULT_EMAIL_SUBJECT: dict[str, str] = {
    GuardianDelivery.EventType.WARD_ENROLLED: '{{student_name}} enrolled at {{school_name}}',
    GuardianDelivery.EventType.PAYMENT_RECEIPT: 'Receipt {{receipt_number}} — {{student_name}}',
    GuardianDelivery.EventType.DEBT_REMINDER: 'Fee reminder — {{student_name}}',
    GuardianDelivery.EventType.REPORT_READY: "{{student_name}}'s report is ready",
    GuardianDelivery.EventType.NEXT_TERM_FEES: 'Fee schedule — {{student_name}} ({{term_label}})',
}

DEFAULT_EMAIL_TEXT: dict[str, str] = {
    GuardianDelivery.EventType.WARD_ENROLLED: (
        '{{greeting_line}}{{student_name}} has been enrolled at {{school_name}}{{class_part}}.\n\n'
        'You are listed as a guardian on their school record.\n\n'
        'If you have questions, please contact the school.'
    ),
    GuardianDelivery.EventType.PAYMENT_RECEIPT: (
        '{{greeting_line}}We received a payment of GHS {{amount}} for {{student_name}}.\n\n'
        'Receipt {{receipt_number}}\n'
        'Download: {{receipt_url}}'
    ),
    GuardianDelivery.EventType.DEBT_REMINDER: (
        '{{greeting_line}}This is a reminder that {{student_name}} has an outstanding balance '
        'of GHS {{balance}} for {{term_label}}.\n\n'
        'Please contact the school to arrange payment.'
    ),
    GuardianDelivery.EventType.REPORT_READY: (
        '{{greeting_line}}{{student_name}}\'s report for {{term_label}} is ready.\n\n'
        'Download: {{report_url}}'
    ),
    GuardianDelivery.EventType.NEXT_TERM_FEES: (
        '{{greeting_line}}Fee schedule for {{student_name}} ({{term_label}}).\n\n'
        'Total: GHS {{total_display}}\n'
        'Details: {{schedule_url}}'
    ),
}

EMAIL_DJANGO_BASE: dict[str, str] = {
    GuardianDelivery.EventType.WARD_ENROLLED: 'notifications/email/guardian_ward_enrolled',
    GuardianDelivery.EventType.PAYMENT_RECEIPT: 'notifications/email/guardian_payment_receipt',
    GuardianDelivery.EventType.DEBT_REMINDER: 'notifications/email/guardian_debt_reminder',
    GuardianDelivery.EventType.REPORT_READY: 'notifications/email/guardian_report_ready',
    GuardianDelivery.EventType.NEXT_TERM_FEES: 'notifications/email/guardian_next_term_fees',
}

PLACEHOLDERS: dict[str, list[dict[str, str]]] = {
    GuardianDelivery.EventType.WARD_ENROLLED: [
        {'key': 'student_name', 'label': 'Student name'},
        {'key': 'school_name', 'label': 'School name'},
        {'key': 'class_part', 'label': 'Class suffix e.g. (P1)'},
        {'key': 'greeting_line', 'label': 'Email greeting line'},
    ],
    GuardianDelivery.EventType.PAYMENT_RECEIPT: [
        {'key': 'student_name', 'label': 'Student name'},
        {'key': 'school_name', 'label': 'School name'},
        {'key': 'amount', 'label': 'Amount'},
        {'key': 'receipt_number', 'label': 'Receipt number'},
        {'key': 'receipt_url', 'label': 'Receipt link'},
        {'key': 'greeting_line', 'label': 'Email greeting line'},
    ],
    GuardianDelivery.EventType.DEBT_REMINDER: [
        {'key': 'student_name', 'label': 'Student name'},
        {'key': 'school_name', 'label': 'School name'},
        {'key': 'balance', 'label': 'Balance'},
        {'key': 'term_label', 'label': 'Term label'},
        {'key': 'terms_summary', 'label': 'Terms summary (all-time)'},
        {'key': 'greeting_line', 'label': 'Email greeting line'},
    ],
    GuardianDelivery.EventType.REPORT_READY: [
        {'key': 'student_name', 'label': 'Student name'},
        {'key': 'school_name', 'label': 'School name'},
        {'key': 'term_label', 'label': 'Term label'},
        {'key': 'report_url', 'label': 'Report link'},
        {'key': 'greeting_line', 'label': 'Email greeting line'},
    ],
    GuardianDelivery.EventType.NEXT_TERM_FEES: [
        {'key': 'student_name', 'label': 'Student name'},
        {'key': 'school_name', 'label': 'School name'},
        {'key': 'term_label', 'label': 'Term label'},
        {'key': 'total_display', 'label': 'Total amount'},
        {'key': 'schedule_url', 'label': 'Fee schedule link'},
        {'key': 'greeting_line', 'label': 'Email greeting line'},
    ],
}

EVENT_LABELS = {
    GuardianDelivery.EventType.WARD_ENROLLED: 'Ward enrolled',
    GuardianDelivery.EventType.PAYMENT_RECEIPT: 'Payment + receipt link',
    GuardianDelivery.EventType.DEBT_REMINDER: 'Debt reminders',
    GuardianDelivery.EventType.REPORT_READY: 'Report ready',
    GuardianDelivery.EventType.NEXT_TERM_FEES: 'Next-term fees',
}


def sms_prefix(*, school_name: str) -> str:
    sender = getattr(settings, 'ARKESEL_SMS_SENDER', None) or 'SCHOOLASST'
    return f'{sender} [{school_name}]'


def render_placeholders(template: str, context: dict[str, Any]) -> str:
    def _replace(match: re.Match) -> str:
        key = match.group(1)
        value = context.get(key, '')
        return '' if value is None else str(value)

    return PLACEHOLDER_RE.sub(_replace, template or '')


def validate_placeholders(template: str, *, event_type: str) -> None:
    allowed = {row['key'] for row in PLACEHOLDERS.get(event_type, [])}
    unknown = sorted({m.group(1) for m in PLACEHOLDER_RE.finditer(template or '')} - allowed)
    if unknown:
        raise ValidationError({
            'detail': f'Unknown placeholders: {", ".join("{{" + k + "}}" for k in unknown)}',
        })


def sample_context(*, school_name: str, event_type: str) -> dict[str, str]:
    base = {
        'school_name': school_name or 'Demo School',
        'student_name': 'Ama Mensah',
        'greeting_line': 'Hi Kofi Mensah,\n\n',
        'class_part': ' (Primary 3)',
        'amount': '150.00',
        'receipt_number': 'RCP-1042',
        'receipt_url': 'https://example.com/r/sample',
        'balance': '320.00',
        'term_label': '2025/2026 · Term 1',
        'terms_summary': 'Term 1, Term 2',
        'report_url': 'https://example.com/reports/sample',
        'total_display': '850.00',
        'schedule_url': 'https://example.com/fees/sample',
    }
    if event_type == GuardianDelivery.EventType.WARD_ENROLLED:
        base['class_part'] = ' (Primary 3)'
    return base


def get_or_none_template(school, event_type: str) -> GuardianMessageTemplate | None:
    return GuardianMessageTemplate.objects.filter(school=school, event_type=event_type).first()


def effective_sms_body(school, event_type: str, *, all_time: bool = False) -> str:
    row = get_or_none_template(school, event_type)
    if all_time and event_type == GuardianDelivery.EventType.DEBT_REMINDER:
        custom = (row.sms_body_all_time if row else '') or ''
        return custom.strip() or DEFAULT_SMS_ALL_TIME
    custom = (row.sms_body if row else '') or ''
    return custom.strip() or DEFAULT_SMS[event_type]


def effective_email_subject(school, event_type: str) -> str:
    row = get_or_none_template(school, event_type)
    custom = (row.email_subject if row else '') or ''
    return custom.strip() or DEFAULT_EMAIL_SUBJECT[event_type]


def effective_email_text(school, event_type: str) -> str | None:
    """Return custom email text if set; None means use Django HTML/text templates."""
    row = get_or_none_template(school, event_type)
    custom = (row.email_text if row else '') or ''
    return custom.strip() or None


def effective_email_html(school, event_type: str) -> str | None:
    row = get_or_none_template(school, event_type)
    custom = (row.email_html if row else '') or ''
    return custom.strip() or None


def compose_sms(*, school, event_type: str, context: dict[str, Any], all_time: bool = False) -> str:
    school_name = context.get('school_name') or getattr(school, 'name', '') or 'School'
    body = render_placeholders(
        effective_sms_body(school, event_type, all_time=all_time),
        {**context, 'school_name': school_name},
    )
    return f'{sms_prefix(school_name=school_name)}: {body}'


def compose_email(
    *,
    school,
    event_type: str,
    context: dict[str, Any],
) -> tuple[str, str, str]:
    """Return (subject, text_body, html_body)."""
    school_name = context.get('school_name') or getattr(school, 'name', '') or 'School'
    ctx = {**context, 'school_name': school_name}
    if 'greeting_line' not in ctx:
        greeting = (ctx.get('greeting') or '').strip()
        ctx['greeting_line'] = f'{greeting}\n\n' if greeting else ''

    subject = render_placeholders(effective_email_subject(school, event_type), ctx)
    custom_text = effective_email_text(school, event_type)
    custom_html = effective_email_html(school, event_type)

    if custom_text is None and custom_html is None:
        base = EMAIL_DJANGO_BASE[event_type]
        text_body = render_to_string(f'{base}.txt', ctx)
        html_body = render_to_string(f'{base}.html', ctx)
        return subject, text_body, html_body

    text_body = render_placeholders(custom_text or DEFAULT_EMAIL_TEXT[event_type], ctx)
    if custom_html:
        html_body = render_placeholders(custom_html, ctx)
    else:
        escaped = html.escape(text_body).replace('\n', '<br>\n')
        html_body = f'<div style="font-family:sans-serif;font-size:15px;line-height:1.5">{escaped}</div>'
    return subject, text_body, html_body


def list_templates_for_school(school) -> list[dict]:
    rows = {
        row.event_type: row
        for row in GuardianMessageTemplate.objects.filter(school=school)
    }
    payload = []
    for event_type, label in EVENT_LABELS.items():
        row = rows.get(event_type)
        sms_default = DEFAULT_SMS[event_type]
        sms_custom = (row.sms_body if row else '') or ''
        sms_all_default = (
            DEFAULT_SMS_ALL_TIME
            if event_type == GuardianDelivery.EventType.DEBT_REMINDER
            else ''
        )
        sms_all_custom = (row.sms_body_all_time if row else '') or ''
        email_subject_default = DEFAULT_EMAIL_SUBJECT[event_type]
        email_subject_custom = (row.email_subject if row else '') or ''
        email_text_default = DEFAULT_EMAIL_TEXT[event_type]
        email_text_custom = (row.email_text if row else '') or ''
        email_html_custom = (row.email_html if row else '') or ''
        payload.append({
            'event_type': event_type,
            'label': label,
            'placeholders': PLACEHOLDERS[event_type],
            'sms_prefix_example': f'{sms_prefix(school_name=school.name)}:',
            'sms_body': sms_custom or sms_default,
            'sms_body_is_custom': bool(sms_custom.strip()),
            'sms_body_default': sms_default,
            'sms_body_all_time': (
                (sms_all_custom or sms_all_default)
                if event_type == GuardianDelivery.EventType.DEBT_REMINDER
                else ''
            ),
            'sms_body_all_time_is_custom': bool(sms_all_custom.strip()),
            'sms_body_all_time_default': sms_all_default,
            'email_subject': email_subject_custom or email_subject_default,
            'email_subject_is_custom': bool(email_subject_custom.strip()),
            'email_subject_default': email_subject_default,
            'email_text': email_text_custom or email_text_default,
            'email_text_is_custom': bool(email_text_custom.strip()),
            'email_text_default': email_text_default,
            'email_html': email_html_custom,
            'email_html_is_custom': bool(email_html_custom.strip()),
            'updated_at': row.updated_at.isoformat() if row else None,
        })
    return payload


def upsert_template(
    *,
    school,
    event_type: str,
    sms_body: str | None = None,
    sms_body_all_time: str | None = None,
    email_subject: str | None = None,
    email_text: str | None = None,
    email_html: str | None = None,
    restore: list[str] | None = None,
) -> GuardianMessageTemplate:
    if event_type not in EVENT_LABELS:
        raise ValidationError({'event_type': 'Unknown event type.'})

    restore_set = set(restore or [])
    row, _ = GuardianMessageTemplate.objects.get_or_create(
        school=school,
        event_type=event_type,
    )

    if 'sms_body' in restore_set:
        row.sms_body = ''
    elif sms_body is not None:
        validate_placeholders(sms_body, event_type=event_type)
        row.sms_body = sms_body.strip()

    if event_type == GuardianDelivery.EventType.DEBT_REMINDER:
        if 'sms_body_all_time' in restore_set:
            row.sms_body_all_time = ''
        elif sms_body_all_time is not None:
            validate_placeholders(sms_body_all_time, event_type=event_type)
            row.sms_body_all_time = sms_body_all_time.strip()

    if 'email_subject' in restore_set:
        row.email_subject = ''
    elif email_subject is not None:
        validate_placeholders(email_subject, event_type=event_type)
        row.email_subject = email_subject.strip()[:200]

    if 'email_text' in restore_set:
        row.email_text = ''
    elif email_text is not None:
        validate_placeholders(email_text, event_type=event_type)
        row.email_text = email_text.strip()

    if 'email_html' in restore_set:
        row.email_html = ''
    elif email_html is not None:
        validate_placeholders(email_html, event_type=event_type)
        row.email_html = email_html.strip()

    row.save()
    return row


def preview_template(
    *,
    school,
    event_type: str,
    channel: str,
    sms_body: str | None = None,
    sms_body_all_time: str | None = None,
    email_subject: str | None = None,
    email_text: str | None = None,
    all_time: bool = False,
) -> dict:
    if event_type not in EVENT_LABELS:
        raise ValidationError({'event_type': 'Unknown event type.'})
    if channel not in ('sms', 'email'):
        raise ValidationError({'channel': 'channel must be sms or email.'})

    ctx = sample_context(school_name=school.name, event_type=event_type)

    if channel == 'sms':
        if all_time and event_type == GuardianDelivery.EventType.DEBT_REMINDER:
            raw = sms_body_all_time
            if raw is None:
                raw = effective_sms_body(school, event_type, all_time=True)
        else:
            raw = sms_body
            if raw is None:
                raw = effective_sms_body(school, event_type, all_time=False)
        validate_placeholders(raw, event_type=event_type)
        rendered_body = render_placeholders(raw, ctx)
        full = f'{sms_prefix(school_name=school.name)}: {rendered_body}'
        analysis = analyze_sms(full)
        return {
            'event_type': event_type,
            'channel': 'sms',
            'prefix': f'{sms_prefix(school_name=school.name)}:',
            'rendered_body': rendered_body,
            'rendered': full,
            'sms': analysis,
        }

    subject_raw = email_subject if email_subject is not None else effective_email_subject(school, event_type)
    text_raw = email_text if email_text is not None else (
        effective_email_text(school, event_type) or DEFAULT_EMAIL_TEXT[event_type]
    )
    validate_placeholders(subject_raw, event_type=event_type)
    validate_placeholders(text_raw, event_type=event_type)
    subject = render_placeholders(subject_raw, ctx)
    text = render_placeholders(text_raw, ctx)
    return {
        'event_type': event_type,
        'channel': 'email',
        'rendered_subject': subject,
        'rendered': text,
        'characters': len(text),
    }
