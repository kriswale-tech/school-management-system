from django.http import HttpResponseBadRequest, HttpResponseNotFound
from django.views import View

from assessments.services.report_links import load_report_from_token
from assessments.services.report_pdf import _signed_url


class PublicReportView(View):
    """Unauthenticated report download opened from a signed guardian link."""

    def get(self, request, token: str):
        try:
            report = load_report_from_token(token)
        except ValueError as exc:
            message = str(exc)
            if 'not found' in message.lower() or 'unavailable' in message.lower():
                return HttpResponseNotFound(message)
            return HttpResponseBadRequest(message)

        url = _signed_url(report)
        if not url:
            return HttpResponseNotFound('Report file is unavailable.')

        from django.shortcuts import redirect

        return redirect(url)
