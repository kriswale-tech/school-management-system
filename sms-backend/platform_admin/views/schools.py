from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import StandardResultsSetPagination
from platform_admin.authentication import PlatformJWTCookieAuthentication
from platform_admin.models import SchoolAdminInvite
from platform_admin.permissions import IsPlatformAuthenticated
from platform_admin.serializers import (
    PlatformSchoolAuditSerializer,
    PlatformSchoolCreateSerializer,
    PlatformSchoolListSerializer,
    PlatformSchoolSerializer,
    PlatformSchoolStatusSerializer,
    PlatformSchoolSummarySerializer,
    SchoolAdminInviteSerializer,
)
from platform_admin.services import schools as school_services
from platform_admin.utils import client_ip
from schools.models import School


def _get_school_or_404(pk) -> School:
    school = School.objects.filter(pk=pk).first()
    if school is None:
        raise NotFound('School not found.')
    return school


class PlatformSchoolListCreateView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        parameters=[
            OpenApiParameter('status', str, required=False),
            OpenApiParameter('search', str, required=False),
        ],
        responses={200: PlatformSchoolListSerializer(many=True)},
    )
    def get(self, request):
        qs = school_services.school_queryset()
        status_filter = (request.query_params.get('status') or '').strip()
        search = (request.query_params.get('search') or '').strip()
        if status_filter:
            qs = qs.filter(status=status_filter)
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(phone_number__icontains=search)
                | Q(email__icontains=search)
                | Q(region__icontains=search),
            )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = PlatformSchoolListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        request=PlatformSchoolCreateSerializer,
        responses={201: PlatformSchoolSerializer},
    )
    def post(self, request):
        serializer = PlatformSchoolCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        school = school_services.create_school_for_platform(
            actor=request.platform_user,
            ip_address=client_ip(request),
            **serializer.validated_data,
        )
        return Response(
            PlatformSchoolSerializer(school).data,
            status=status.HTTP_201_CREATED,
        )


class PlatformSchoolSummaryView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(responses={200: PlatformSchoolSummarySerializer})
    def get(self, request):
        payload = school_services.school_directory_summary()
        return Response(PlatformSchoolSummarySerializer(payload).data)


class PlatformSchoolDetailView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(responses={200: PlatformSchoolSerializer})
    def get(self, request, pk):
        school = _get_school_or_404(pk)
        payload = PlatformSchoolSerializer(school).data
        payload['admins'] = [
            {
                'membership_id': str(m.id),
                'user_id': str(m.user_id),
                'phone_number': m.user.phone_number,
                'email': m.user.email or '',
                'full_name': m.user.get_full_name(),
                'role': m.role,
                'is_active': m.is_active,
            }
            for m in school_services.school_admin_memberships(school)
        ]
        payload['invites'] = SchoolAdminInviteSerializer(
            SchoolAdminInvite.objects.filter(school=school).order_by('-created_at')[:20],
            many=True,
        ).data
        payload['staff_count'] = school_services.active_staff_count(school)
        payload['student_count'] = school_services.active_student_count(school)
        payload['status_reason'] = school_services.latest_status_reason(school)
        return Response(payload)

    @extend_schema(
        request=PlatformSchoolSerializer,
        responses={200: PlatformSchoolSerializer},
    )
    def patch(self, request, pk):
        school = _get_school_or_404(pk)
        serializer = PlatformSchoolSerializer(school, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        school = school_services.update_school_for_platform(
            actor=request.platform_user,
            school=school,
            data=serializer.validated_data,
            ip_address=client_ip(request),
        )
        return Response(PlatformSchoolSerializer(school).data)


class PlatformSchoolStatusView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(
        request=PlatformSchoolStatusSerializer,
        responses={200: PlatformSchoolSerializer},
    )
    def post(self, request, pk):
        school = _get_school_or_404(pk)
        serializer = PlatformSchoolStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        school = school_services.set_school_status(
            actor=request.platform_user,
            school=school,
            status=serializer.validated_data['status'],
            reason=serializer.validated_data['reason'],
            ip_address=client_ip(request),
        )
        return Response(PlatformSchoolSerializer(school).data)


class PlatformSchoolAuditView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]
    pagination_class = StandardResultsSetPagination

    @extend_schema(responses={200: PlatformSchoolAuditSerializer(many=True)})
    def get(self, request, pk):
        school = _get_school_or_404(pk)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(
            school_services.school_audit_logs(school),
            request,
            view=self,
        )
        serializer = PlatformSchoolAuditSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
