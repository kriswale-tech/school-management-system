from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from platform_admin.authentication import PlatformJWTCookieAuthentication
from platform_admin.models import SchoolAdminInvite
from platform_admin.permissions import IsPlatformAuthenticated
from platform_admin.serializers import (
    SchoolAdminInviteCreateSerializer,
    SchoolAdminInviteSerializer,
)
from platform_admin.services import invites as invite_services
from platform_admin.utils import client_ip
from schools.models import School


class PlatformSchoolInviteCreateView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(
        request=SchoolAdminInviteCreateSerializer,
        responses={201: SchoolAdminInviteSerializer},
    )
    def post(self, request, pk):
        school = School.objects.filter(pk=pk).first()
        if school is None:
            raise NotFound('School not found.')
        serializer = SchoolAdminInviteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invite = invite_services.create_admin_invite(
            actor=request.platform_user,
            school=school,
            ip_address=client_ip(request),
            **serializer.validated_data,
        )
        return Response(
            SchoolAdminInviteSerializer(invite).data,
            status=status.HTTP_201_CREATED,
        )


class PlatformSchoolInviteResendView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(responses={200: SchoolAdminInviteSerializer})
    def post(self, request, pk, invite_id):
        invite = (
            SchoolAdminInvite.objects.select_related('school')
            .filter(pk=invite_id, school_id=pk)
            .first()
        )
        if invite is None:
            raise NotFound('Invite not found.')
        invite = invite_services.resend_admin_invite(
            actor=request.platform_user,
            invite=invite,
            ip_address=client_ip(request),
        )
        return Response(SchoolAdminInviteSerializer(invite).data)
