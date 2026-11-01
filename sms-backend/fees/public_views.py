from django.http import HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import render
from django.views import View

from fees.services.fee_schedule_links import (
    build_fee_schedule_context,
    load_fee_schedule_from_token,
)
from fees.services.receipts import build_receipt_context, load_receipt_from_token


class PublicReceiptView(View):
    """Unauthenticated receipt page opened from a signed guardian link."""

    def get(self, request, token: str):
        try:
            receipt = load_receipt_from_token(token)
        except ValueError as exc:
            message = str(exc)
            if 'not found' in message.lower():
                return HttpResponseNotFound(message)
            return HttpResponseBadRequest(message)

        context = build_receipt_context(receipt)
        response = render(request, 'fees/public/receipt.html', context)
        response['Content-Disposition'] = (
            f'inline; filename="{receipt.receipt_number}.html"'
        )
        return response


class PublicFeeScheduleView(View):
    """Unauthenticated per-student fee schedule from a signed guardian link."""

    def get(self, request, token: str):
        try:
            student, term, fees = load_fee_schedule_from_token(token)
        except ValueError as exc:
            message = str(exc)
            if 'not found' in message.lower():
                return HttpResponseNotFound(message)
            return HttpResponseBadRequest(message)

        context = build_fee_schedule_context(student=student, term=term, fees=fees)
        filename = f'fees-{student.student_id}-{term.id}.html'
        response = render(request, 'fees/public/fee_schedule.html', context)
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
