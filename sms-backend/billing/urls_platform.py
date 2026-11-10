from django.urls import path

from billing.views import (
    PlatformDiscountDetailView,
    PlatformDiscountListCreateView,
    PlatformDiscountRestoreView,
    PlatformDiscountRevokeView,
    PlatformInvoiceMarkPaidView,
    PlatformPaymentListView,
    PlatformPlanDetailView,
    PlatformPlanListCreateView,
    PlatformPlanSeedView,
    PlatformSchoolCapacityUpgradeView,
    PlatformSchoolChangeIntervalView,
    PlatformSchoolInvoiceListView,
    PlatformSchoolPaymentListView,
    PlatformSchoolScheduleChangeView,
    PlatformSchoolSubscriptionView,
    PlatformTopUpPackageDetailView,
    PlatformTopUpPackageListCreateView,
    PlatformTopUpPackageSeedView,
)

urlpatterns = [
    path('discounts/', PlatformDiscountListCreateView.as_view(), name='platform-billing-discounts'),
    path(
        'discounts/<uuid:pk>/',
        PlatformDiscountDetailView.as_view(),
        name='platform-billing-discount-detail',
    ),
    path(
        'discounts/<uuid:pk>/redemptions/<uuid:redemption_id>/revoke/',
        PlatformDiscountRevokeView.as_view(),
        name='platform-billing-discount-revoke',
    ),
    path(
        'discounts/<uuid:pk>/redemptions/<uuid:redemption_id>/restore/',
        PlatformDiscountRestoreView.as_view(),
        name='platform-billing-discount-restore',
    ),
    path('plans/', PlatformPlanListCreateView.as_view(), name='platform-billing-plans'),
    path('plans/seed/', PlatformPlanSeedView.as_view(), name='platform-billing-plans-seed'),
    path('plans/<uuid:pk>/', PlatformPlanDetailView.as_view(), name='platform-billing-plan-detail'),
    path('topups/', PlatformTopUpPackageListCreateView.as_view(), name='platform-billing-topups'),
    path(
        'topups/seed/',
        PlatformTopUpPackageSeedView.as_view(),
        name='platform-billing-topups-seed',
    ),
    path(
        'topups/<uuid:pk>/',
        PlatformTopUpPackageDetailView.as_view(),
        name='platform-billing-topup-detail',
    ),
    path('payments/', PlatformPaymentListView.as_view(), name='platform-billing-payments'),
    path(
        'schools/<uuid:pk>/subscription/',
        PlatformSchoolSubscriptionView.as_view(),
        name='platform-school-subscription',
    ),
    path(
        'schools/<uuid:pk>/subscription/schedule-change/',
        PlatformSchoolScheduleChangeView.as_view(),
        name='platform-school-subscription-schedule',
    ),
    path(
        'schools/<uuid:pk>/subscription/capacity-upgrade/',
        PlatformSchoolCapacityUpgradeView.as_view(),
        name='platform-school-capacity-upgrade',
    ),
    path(
        'schools/<uuid:pk>/subscription/change-interval/',
        PlatformSchoolChangeIntervalView.as_view(),
        name='platform-school-change-interval',
    ),
    path(
        'schools/<uuid:pk>/invoices/',
        PlatformSchoolInvoiceListView.as_view(),
        name='platform-school-invoices',
    ),
    path(
        'schools/<uuid:pk>/payments/',
        PlatformSchoolPaymentListView.as_view(),
        name='platform-school-payments',
    ),
    path(
        'invoices/<uuid:pk>/mark-paid/',
        PlatformInvoiceMarkPaidView.as_view(),
        name='platform-invoice-mark-paid',
    ),
]
