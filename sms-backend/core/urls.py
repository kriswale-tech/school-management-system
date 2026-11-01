from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from assessments.public_views import PublicReportView
from fees.public_views import PublicFeeScheduleView, PublicReceiptView

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
]
