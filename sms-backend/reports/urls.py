from django.urls import path

from reports.views import (
    ReportsByClassView,
    ReportsBySubjectView,
    ReportsEnrollmentView,
    ReportsFeesAcademicRiskView,
    ReportsFilterOptionsView,
    ReportsFinanceView,
    ReportsGradeDistributionView,
    ReportsOverviewView,
    ReportsStaffCapacityView,
    ReportsStudentTrendsView,
    ReportsSubjectHeatmapView,
    ReportsTeacherDeskView,
    ReportsWorkflowView,
)

urlpatterns = [
    path('filters/', ReportsFilterOptionsView.as_view(), name='reports-filters'),
    path('overview/', ReportsOverviewView.as_view(), name='reports-overview'),
    path('by-class/', ReportsByClassView.as_view(), name='reports-by-class'),
    path('by-subject/', ReportsBySubjectView.as_view(), name='reports-by-subject'),
    path(
        'grade-distribution/',
        ReportsGradeDistributionView.as_view(),
        name='reports-grade-distribution',
    ),
    path('student-trends/', ReportsStudentTrendsView.as_view(), name='reports-student-trends'),
    path('subject-heatmap/', ReportsSubjectHeatmapView.as_view(), name='reports-subject-heatmap'),
    path('workflow/', ReportsWorkflowView.as_view(), name='reports-workflow'),
    path(
        'fees-academic-risk/',
        ReportsFeesAcademicRiskView.as_view(),
        name='reports-fees-academic-risk',
    ),
    path('finance/', ReportsFinanceView.as_view(), name='reports-finance'),
    path('enrollment/', ReportsEnrollmentView.as_view(), name='reports-enrollment'),
    path('staff-capacity/', ReportsStaffCapacityView.as_view(), name='reports-staff-capacity'),
    path('teacher-desk/', ReportsTeacherDeskView.as_view(), name='reports-teacher-desk'),
]
