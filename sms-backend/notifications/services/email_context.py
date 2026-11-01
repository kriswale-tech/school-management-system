"""Build template context for notification emails (send wiring comes later)."""

from django.conf import settings


def default_app_logo_url() -> str:
    """Absolute URL for the SMS wordmark used when a school has no logo."""
    base = getattr(settings, 'FRONTEND_URL', 'http://localhost:3003').rstrip('/')
    return f'{base}/email/app-logo.svg'


def build_notification_email_context(
    *,
    school,
    title: str,
    body: str,
    cta_path: str = '',
    cta_label: str = 'Open in app',
    greeting: str = '',
    preheader: str = '',
    body_html: str = '',
    meta_label: str = '',
    meta_value: str = '',
    footer_note: str = '',
    recipient_name: str = '',
) -> dict:
    """Context keys expected by notifications/email/notification.html."""
    frontend = getattr(settings, 'FRONTEND_URL', 'http://localhost:3003').rstrip('/')
    logo_url = ''
    if getattr(school, 'logo', None):
        try:
            logo_url = school.logo.url
        except (ValueError, AttributeError):
            logo_url = ''

    if not greeting and recipient_name:
        greeting = f'Hi {recipient_name},'

    cta_url = ''
    if cta_path:
        if cta_path.startswith('http://') or cta_path.startswith('https://'):
            cta_url = cta_path
        else:
            cta_url = f'{frontend}{cta_path if cta_path.startswith("/") else f"/{cta_path}"}'

    return {
        'school_name': school.name,
        'school_logo_url': logo_url or None,
        'app_logo_url': default_app_logo_url(),
        'title': title,
        'body': body,
        'body_html': body_html,
        'greeting': greeting,
        'preheader': preheader or body[:120],
        'cta_url': cta_url,
        'cta_label': cta_label,
        'meta_label': meta_label,
        'meta_value': meta_value,
        'footer_note': footer_note,
    }
