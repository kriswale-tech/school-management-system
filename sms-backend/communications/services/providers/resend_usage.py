"""Legacy module path — email usage sync now lives in ``ses_usage``."""

from communications.services.providers.ses_usage import (  # noqa: F401
    fetch_ses_usage_placeholder as fetch_resend_usage,
    latest_resend_snapshot,
    latest_ses_snapshot,
    parse_usage_payload,
    sync_resend_usage,
    sync_ses_usage,
)

RESEND_USAGE_URL = ''
