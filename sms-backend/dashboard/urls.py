from django.urls import path

from dashboard.views import AdminDashboardView

urlpatterns = [
    path('admin/', AdminDashboardView.as_view(), name='dashboard-admin'),
]
