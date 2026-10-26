from drf_spectacular.utils import extend_schema
from rest_framework.response import Response

from accounts.permissions import HasActiveSchool, IsAdmin, IsStaff, IsTeacher
from dashboard.serializers import (
    AdminDashboardSerializer,
    StaffDashboardSerializer,
    TeacherDashboardSerializer,
)
from dashboard.services import get_admin_dashboard, get_staff_dashboard, get_teacher_dashboard
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


class TeacherDashboardView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, IsTeacher]

    @extend_schema(
        tags=['Dashboard'],
        summary='Teacher dashboard overview',
        description=(
            'Classes, subjects, assessment progress, and recent activity for the '
            'signed-in teacher this term.'
        ),
        responses={200: TeacherDashboardSerializer},
    )
    def get(self, request):
        payload = get_teacher_dashboard(school=self.school, membership=self.membership)
        return Response(TeacherDashboardSerializer(payload).data)


class StaffDashboardView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, IsStaff]

    @extend_schema(
        tags=['Dashboard'],
        summary='Staff dashboard overview',
        description=(
            'School and academic overview for staff: students/classes/teachers, '
            'report workflow, coverage gaps, needs-attention, and recent activity. '
            'No fee data.'
        ),
        responses={200: StaffDashboardSerializer},
    )
    def get(self, request):
        payload = get_staff_dashboard(school=self.school)
        return Response(StaffDashboardSerializer(payload).data)
