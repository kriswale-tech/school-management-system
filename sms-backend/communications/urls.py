from django.urls import path

from communications.views import (
    SchoolAddonScheduleView,
    SchoolAddonSkuCatalogView,
    SchoolCreditsView,
    SchoolLedgerView,
)

urlpatterns = [
    path('skus/', SchoolAddonSkuCatalogView.as_view(), name='school-comms-skus'),
    path('credits/', SchoolCreditsView.as_view(), name='school-comms-credits'),
    path('ledger/', SchoolLedgerView.as_view(), name='school-comms-ledger'),
    path('addons/schedule/', SchoolAddonScheduleView.as_view(), name='school-comms-addon-schedule'),
]
