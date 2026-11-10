from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from assessments.public_views import PublicReportView
from fees.public_views import PublicFeeScheduleView, PublicReceiptView
from notifications.views_webhooks import (
    ArkeselSmsDlrWebhookView,
    ResendWebhookView,
    SesWebhookView,
)

v1_path = 'api/v1/'

urlpatterns = [
    # admin urls
    path(f'{v1_path}admin/', admin.site.urls),

    # drf spectacular urls (api docs)
    path(f'{v1_path}schema/', SpectacularAPIView.as_view(), name='schema'),
    path(f'{v1_path}docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # public (no auth) — signed guardian links
    path(
        f'{v1_path}public/receipts/<path:token>/',
        PublicReceiptView.as_view(),
        name='public-receipt',
    ),
    path(
        f'{v1_path}public/fee-schedules/<path:token>/',
        PublicFeeScheduleView.as_view(),
        name='public-fee-schedule',
    ),
    path(
        f'{v1_path}public/reports/<path:token>/',
        PublicReportView.as_view(),
        name='public-report',
    ),
    # public (no auth) — Arkesel SMS delivery reports (callback_url)
    path(
        f'{v1_path}webhooks/arkesel/sms-dlr/',
        ArkeselSmsDlrWebhookView.as_view(),
        name='arkesel-sms-dlr-webhook',
    ),
    # public (no auth) — Amazon SES email events (SNS → HTTP)
    path(
        f'{v1_path}webhooks/ses/',
        SesWebhookView.as_view(),
        name='ses-webhook',
    ),
    # legacy — Resend email events (Svix-signed)
    path(
        f'{v1_path}webhooks/resend/',
        ResendWebhookView.as_view(),
        name='resend-webhook',
    ),

    # api urls
    path(f'{v1_path}accounts/', include('accounts.urls')),
    path(f'{v1_path}academics/', include('academics.urls')),
    path(f'{v1_path}schools/', include('schools.urls')),
    path(f'{v1_path}students/', include('students.urls')),
    path(f'{v1_path}fees/', include('fees.urls')),
    path(f'{v1_path}dashboard/', include('dashboard.urls')),
    path(f'{v1_path}activities/', include('activities.urls')),
    path(f'{v1_path}reports/', include('reports.urls')),
    path(f'{v1_path}notifications/', include('notifications.urls')),
    path(f'{v1_path}platform/', include('platform_admin.urls')),
    path(f'{v1_path}platform/billing/', include('billing.urls_platform')),
    path(f'{v1_path}platform/communications/', include('communications.urls_platform')),
    path(f'{v1_path}platform/messages/', include('communications.urls_messages')),
    path(f'{v1_path}billing/', include('billing.urls')),
    path(f'{v1_path}communications/', include('communications.urls')),
    path(f'{v1_path}messaging/', include('messaging.urls')),
]
