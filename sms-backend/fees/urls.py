from django.urls import path

from fees.views import (
    ApplyFeeStructureView,
    FeeDeskFilterOptionsView,
    FeeDeskListView,
    FeeDeskStatsView,
    FeeStructureDetailView,
    FeeStructureItemCreateView,
    FeeStructureItemDetailView,
    RecordPaymentView,
    StudentPaymentTargetView,
)

urlpatterns = [
    path('', FeeDeskListView.as_view(), name='fee-desk-list'),
    path('stats/', FeeDeskStatsView.as_view(), name='fee-desk-stats'),
    path('filter-options/', FeeDeskFilterOptionsView.as_view(), name='fee-desk-filter-options'),
    path('payments/', RecordPaymentView.as_view(), name='record-payment'),
    path(
        'students/<uuid:student_id>/payment-target/',
        StudentPaymentTargetView.as_view(),
        name='student-payment-target',
    ),
    path('structures/', FeeStructureDetailView.as_view(), name='fee-structure-detail'),
    path(
        'structures/items/',
        FeeStructureItemCreateView.as_view(),
        name='fee-structure-item-create',
    ),
    path(
        'structures/items/<uuid:fee_item_id>/',
        FeeStructureItemDetailView.as_view(),
        name='fee-structure-item-detail',
    ),
    path(
        'structures/<uuid:structure_id>/apply/',
        ApplyFeeStructureView.as_view(),
        name='fee-structure-apply',
    ),
]
