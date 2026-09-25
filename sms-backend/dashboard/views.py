from drf_spectacular.utils import extend_schema
from rest_framework.response import Response

from accounts.permissions import HasActiveSchool, IsAdmin
from dashboard.serializers import AdminDashboardSerializer
from dashboard.services import get_admin_dashboard
from shared.views import SchoolScopedAPIView


class AdminDashboardView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, IsAdmin]

    @extend_schema(
        tags=['Dashboard'],
        summary='Admin dashboard overview',
        description=(
            'Aggregated actionable overview for school admins: school/fees/academic '
            'stats, needs-attention queue, top debtors, and report completion by class.'
        ),
        responses={200: AdminDashboardSerializer},
    )
    def get(self, request):
        payload = get_admin_dashboard(school=self.school)
        return Response(AdminDashboardSerializer(payload).data)
