from django.urls import path

from students.bulk_views import (
    StudentBulkImportFailuresDownloadView,
    StudentBulkImportTemplateView,
    StudentBulkImportUploadView,
)
from students.views import (
    ParentListView,
    StudentAssessmentReportGenerateView,
    StudentAssessmentReportView,
    StudentAssessmentView,
    StudentCurrentYearFeesView,
    StudentDetailView,
    StudentFeeHistoryView,
    StudentGuardianDetailView,
    StudentGuardianListCreateView,
    StudentListView,
    StudentOnboardView,
    StudentPaymentListView,
    StudentStatsView,
)

urlpatterns = [
    path('', StudentListView.as_view(), name='student-list'),
    path('onboard/', StudentOnboardView.as_view(), name='student-onboard'),
    path('parents/', ParentListView.as_view(), name='parent-list'),
    path('stats/', StudentStatsView.as_view(), name='student-stats'),
    path(
        '<uuid:student_id>/',
        StudentDetailView.as_view(),
        name='student-detail',
    ),
    path(
        '<uuid:student_id>/assessments/',
        StudentAssessmentView.as_view(),
        name='student-assessments',
    ),
    path(
        '<uuid:student_id>/assessments/report/',
        StudentAssessmentReportView.as_view(),
        name='student-assessment-report',
    ),
    path(
        '<uuid:student_id>/assessments/report/generate/',
        StudentAssessmentReportGenerateView.as_view(),
        name='student-assessment-report-generate',
    ),
    path(
        '<uuid:student_id>/fees/',
        StudentCurrentYearFeesView.as_view(),
        name='student-current-year-fees',
    ),
    path(
        '<uuid:student_id>/fees/history/',
        StudentFeeHistoryView.as_view(),
        name='student-fee-history',
    ),
    path(
        '<uuid:student_id>/payments/',
        StudentPaymentListView.as_view(),
        name='student-payment-list',
    ),
    path(
        '<uuid:student_id>/guardians/',
        StudentGuardianListCreateView.as_view(),
        name='student-guardians',
    ),
    path(
        '<uuid:student_id>/guardians/<uuid:link_id>/',
        StudentGuardianDetailView.as_view(),
        name='student-guardian-detail',
    ),
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
