from django.http import HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import redirect
from django.views import View

from fees.services.fee_schedule_links import (
    fee_schedule_file_url,
    load_fee_schedule_from_token,
    publish_fee_schedule_pdf,
)
from fees.services.receipts import load_receipt_from_token, publish_receipt_pdf, receipt_file_url


class PublicReceiptView(View):
    """Unauthenticated receipt link. Redirects to the stored PDF."""

    def get(self, request, token: str):
        try:
            receipt = load_receipt_from_token(token)
        except ValueError as exc:
            message = str(exc)
            if 'not found' in message.lower():
                return HttpResponseNotFound(message)
            return HttpResponseBadRequest(message)

        publish_receipt_pdf(receipt)
        url = receipt_file_url(receipt)
        if not url:
            return HttpResponseNotFound('Receipt file is unavailable.')
        return redirect(url)


class PublicFeeScheduleView(View):
    """Unauthenticated fee-schedule link. Redirects to the stored PDF."""

    def get(self, request, token: str):
        try:
            student, term, _fees = load_fee_schedule_from_token(token)
        except ValueError as exc:
            message = str(exc)
            if 'not found' in message.lower():
                return HttpResponseNotFound(message)
            return HttpResponseBadRequest(message)

        publish_fee_schedule_pdf(student=student, term=term)
        url = fee_schedule_file_url(student=student, term=term)
        if not url:
            return HttpResponseNotFound('Fee schedule file is unavailable.')
        return redirect(url)
