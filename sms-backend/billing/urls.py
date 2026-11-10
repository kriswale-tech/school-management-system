from django.urls import path

from billing.views import (
    PaystackSaaSWebhookView,
    SchoolCapacityUpgradeView,
    SchoolCapacityView,
    SchoolChangeIntervalView,
    SchoolInvoiceListView,
    SchoolInvoicePayView,
    SchoolPaymentListView,
    SchoolPaymentStatsView,
    SchoolPaymentVerifyView,
    SchoolPlanCatalogView,
    SchoolSchedulePlanChangeView,
    SchoolSubscriptionView,
    SchoolTopUpPackageListView,
    SchoolTopUpPurchaseView,
    SchoolUpcomingBillView,
)

urlpatterns = [
    path('plans/', SchoolPlanCatalogView.as_view(), name='school-billing-plans'),
    path('subscription/', SchoolSubscriptionView.as_view(), name='school-billing-subscription'),
    path('capacity/', SchoolCapacityView.as_view(), name='school-billing-capacity'),
    path('upcoming/', SchoolUpcomingBillView.as_view(), name='school-billing-upcoming'),
    path('invoices/', SchoolInvoiceListView.as_view(), name='school-billing-invoices'),
    path(
        'invoices/<uuid:pk>/pay/',
        SchoolInvoicePayView.as_view(),
        name='school-billing-invoice-pay',
    ),
    path('topups/', SchoolTopUpPackageListView.as_view(), name='school-billing-topups'),
    path(
        'topups/purchase/',
        SchoolTopUpPurchaseView.as_view(),
        name='school-billing-topup-purchase',
    ),
    path('payments/', SchoolPaymentListView.as_view(), name='school-billing-payments'),
    path(
        'payments/stats/',
        SchoolPaymentStatsView.as_view(),
        name='school-billing-payment-stats',
    ),
    path(
        'payments/verify/',
        SchoolPaymentVerifyView.as_view(),
        name='school-billing-payment-verify',
    ),
    path(
        'paystack/webhook/',
        PaystackSaaSWebhookView.as_view(),
        name='school-billing-paystack-webhook',
    ),
    path(
        'subscription/schedule-change/',
        SchoolSchedulePlanChangeView.as_view(),
        name='school-billing-schedule-change',
    ),
    path(
        'subscription/capacity-upgrade/',
        SchoolCapacityUpgradeView.as_view(),
        name='school-billing-capacity-upgrade',
    ),
    path(
        'subscription/change-interval/',
        SchoolChangeIntervalView.as_view(),
        name='school-billing-change-interval',
    ),
]
