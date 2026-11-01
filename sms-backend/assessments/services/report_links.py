"""Public signed report-card links for guardian download (no login)."""

from __future__ import annotations

from django.conf import settings
from django.core import signing
from django.http import Http404
from django.shortcuts import redirect

from assessments.models import Report
from assessments.services.report_pdf import _report_file_exists, _signed_url

REPORT_SALT = 'guardian-report-v1'


def report_link_max_age_seconds() -> int:
    return int(getattr(settings, 'REPORT_LINK_MAX_AGE_SECONDS', 60 * 60 * 24 * 30))


def public_base_url() -> str:
    return getattr(settings, 'PUBLIC_BASE_URL', 'http://localhost:9000').rstrip('/')


def make_report_token(report_id) -> str:
    return signing.dumps({'rid': str(report_id)}, salt=REPORT_SALT)


def build_report_public_url(report_id) -> str:
    token = make_report_token(report_id)
    return f'{public_base_url()}/api/v1/public/reports/{token}/'


def load_report_from_token(token: str) -> Report:
    try:
        payload = signing.loads(
            token,
            salt=REPORT_SALT,
            max_age=report_link_max_age_seconds(),
        )
    except signing.SignatureExpired as exc:
        raise ValueError('This report link has expired.') from exc
    except signing.BadSignature as exc:
        raise ValueError('This report link is invalid.') from exc

    report_id = payload.get('rid')
    if not report_id:
        raise ValueError('This report link is invalid.')

    report = (
        Report.objects.select_related(
            'school',
            'student',
            'stream',
            'term',
            'term__academic_year',
        )
        .filter(id=report_id)
        .first()
    )
    if report is None or not _report_file_exists(report):
        raise ValueError('Report not found.')
    return report


def redirect_to_signed_report(token: str):
    """Resolve token and redirect to a fresh R2/presigned PDF URL."""
    try:
        report = load_report_from_token(token)
    except ValueError as exc:
        raise Http404(str(exc)) from exc
    url = _signed_url(report)
    if not url:
        raise Http404('Report file is unavailable.')
    return redirect(url)
