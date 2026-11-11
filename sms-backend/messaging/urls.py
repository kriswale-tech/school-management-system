from django.urls import path

from messaging.views import (
    MessagingDeliveryBulkRetryView,
    MessagingDeliveryEligibleView,
    MessagingDeliveryListView,
    MessagingDeliveryRetryView,
    MessagingDeliveryVerifyView,
    MessagingOverviewView,
    MessagingTemplateListView,
    MessagingTemplatePreviewView,
    MessagingTemplateUpdateView,
)

urlpatterns = [
    path('overview/', MessagingOverviewView.as_view(), name='messaging-overview'),
    path('deliveries/', MessagingDeliveryListView.as_view(), name='messaging-deliveries'),
    path(
        'deliveries/eligible/',
        MessagingDeliveryEligibleView.as_view(),
        name='messaging-delivery-eligible',
    ),
    path(
        'deliveries/bulk-retry/',
        MessagingDeliveryBulkRetryView.as_view(),
        name='messaging-delivery-bulk-retry',
    ),
    path(
        'deliveries/<uuid:pk>/retry/',
        MessagingDeliveryRetryView.as_view(),
        name='messaging-delivery-retry',
    ),
    path(
        'deliveries/<uuid:pk>/verify/',
        MessagingDeliveryVerifyView.as_view(),
        name='messaging-delivery-verify',
    ),
    path('templates/', MessagingTemplateListView.as_view(), name='messaging-templates'),
    path(
        'templates/update/',
        MessagingTemplateUpdateView.as_view(),
        name='messaging-templates-update',
    ),
    path(
        'templates/preview/',
        MessagingTemplatePreviewView.as_view(),
        name='messaging-templates-preview',
    ),
]
