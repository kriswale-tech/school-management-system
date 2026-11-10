"""Shared test helpers for communication credits."""

from __future__ import annotations

import uuid

from communications.models import CreditAccount
from communications.services.ledger import manual_adjust


def seed_test_credits(school, *, sms: int = 1_000, email: int = 1_000) -> None:
    """Grant SMS/email credits so guardian notify tests can pass credit gates."""
    token = uuid.uuid4().hex[:12]
    if sms > 0:
        manual_adjust(
            school=school,
            channel=CreditAccount.Channel.SMS,
            delta=sms,
            idempotency_key=f'test-credit:sms:{school.pk}:{token}',
            metadata={'source': 'test'},
        )
    if email > 0:
        manual_adjust(
            school=school,
            channel=CreditAccount.Channel.EMAIL,
            delta=email,
            idempotency_key=f'test-credit:email:{school.pk}:{token}',
            metadata={'source': 'test'},
        )
