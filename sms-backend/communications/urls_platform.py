from django.urls import path

from communications.views import (
    PlatformAddonSkuDetailView,
    PlatformAddonSkuListCreateView,
    PlatformAddonSkuSeedView,
    PlatformSchoolAddonScheduleView,
    PlatformSchoolCreditAdjustView,
    PlatformSchoolCreditsView,
    PlatformSchoolLedgerView,
)

urlpatterns = [
    path('skus/', PlatformAddonSkuListCreateView.as_view(), name='platform-comms-skus'),
    path('skus/seed/', PlatformAddonSkuSeedView.as_view(), name='platform-comms-skus-seed'),
    path(
        'skus/<uuid:pk>/',
        PlatformAddonSkuDetailView.as_view(),
        name='platform-comms-sku-detail',
    ),
    path(
        'schools/<uuid:pk>/credits/',
        PlatformSchoolCreditsView.as_view(),
        name='platform-school-credits',
    ),
    path(
        'schools/<uuid:pk>/ledger/',
        PlatformSchoolLedgerView.as_view(),
        name='platform-school-ledger',
    ),
    path(
        'schools/<uuid:pk>/addons/schedule/',
        PlatformSchoolAddonScheduleView.as_view(),
        name='platform-school-addon-schedule',
    ),
    path(
        'schools/<uuid:pk>/credits/adjust/',
        PlatformSchoolCreditAdjustView.as_view(),
        name='platform-school-credit-adjust',
    ),
]
