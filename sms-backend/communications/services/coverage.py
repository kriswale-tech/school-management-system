from __future__ import annotations

from communications.services.ledger import get_balances
from communications.services.segments import units_for_channel


def channel_coverage(
    *,
    school,
    channel: str,
    message_count: int,
    sample_body: str = '',
) -> dict:
    """Estimate whether the current balance can cover a send. Does not debit."""
    count = max(0, int(message_count or 0))
    per_message = units_for_channel(channel=channel, body=sample_body) if count else 0
    needed = per_message * count
    balance = int(get_balances(school).get(channel, 0))
    covered_messages = count if per_message == 0 else min(count, balance // per_message)
    return {
        'balance': balance,
        'per_message': per_message,
        'needed': needed,
        'shortfall_messages': count - covered_messages,
        'sufficient': needed <= balance,
    }


def credit_coverage_for_send(
    *,
    school,
    sms_count: int = 0,
    email_count: int = 0,
    sample_sms: str = '',
    sample_email: str = '',
) -> dict:
    return {
        'sms': channel_coverage(
            school=school,
            channel='sms',
            message_count=sms_count,
            sample_body=sample_sms,
        ),
        'email': channel_coverage(
            school=school,
            channel='email',
            message_count=email_count,
            sample_body=sample_email,
        ),
    }
