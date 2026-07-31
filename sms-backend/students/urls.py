from django.urls import path

from students.bulk_views import (
    StudentBulkImportFailuresDownloadView,
    StudentBulkImportTemplateView,
    StudentBulkImportUploadView,
)
from students.views import (
    ParentListView,
    StudentListView,
    StudentOnboardView,
    StudentStatsView,
)

urlpatterns = [
    path('', StudentListView.as_view(), name='student-list'),
    path('onboard/', StudentOnboardView.as_view(), name='student-onboard'),
    path('parents/', ParentListView.as_view(), name='parent-list'),
    path('stats/', StudentStatsView.as_view(), name='student-stats'),
    path(
        'bulk-upload/template/',
        StudentBulkImportTemplateView.as_view(),
        name='student-bulk-upload-template',
    ),
    path(
        'bulk-upload/',
        StudentBulkImportUploadView.as_view(),
        name='student-bulk-upload',
    ),
    path(
        'bulk-upload/failures/<uuid:token>/',
        StudentBulkImportFailuresDownloadView.as_view(),
        name='student-bulk-upload-failures',
    ),
]
