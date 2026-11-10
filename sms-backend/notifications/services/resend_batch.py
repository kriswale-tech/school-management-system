"""Backward-compatible import path for guardian email batching.

Historically this module talked to Resend. Email now goes through Amazon SES
(with console fallback). Call sites may still ``from notifications.services.resend_batch
import send_email_batch`` — that continues to work.
"""

from notifications.services.email_batch import EMAIL_BATCH_SIZE, send_email_batch

# Legacy aliases so older references keep importing cleanly.
RESEND_EMAIL_BATCH_SIZE = EMAIL_BATCH_SIZE

__all__ = ['EMAIL_BATCH_SIZE', 'RESEND_EMAIL_BATCH_SIZE', 'send_email_batch']
