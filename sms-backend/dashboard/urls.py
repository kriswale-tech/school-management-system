from django.urls import path

from dashboard.views import AdminDashboardView, StaffDashboardView, TeacherDashboardView

urlpatterns = [
    path('admin/', AdminDashboardView.as_view(), name='dashboard-admin'),
    path('teacher/', TeacherDashboardView.as_view(), name='dashboard-teacher'),
    path('staff/', StaffDashboardView.as_view(), name='dashboard-staff'),
]
