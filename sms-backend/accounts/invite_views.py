from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from platform_admin.serializers import (
    SchoolAdminInviteAcceptResponseSerializer,
    SchoolAdminInvitePreviewSerializer,
)
from platform_admin.services import invites as invite_services


class SchoolAdminInvitePreviewView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(responses={200: SchoolAdminInvitePreviewSerializer})
    def get(self, request, token):
        invite = invite_services.refresh_expired_invite(
            invite_services.get_invite_by_token(token),
        )
        return Response(
            SchoolAdminInvitePreviewSerializer(
                {
                    'school_name': invite.school.name,
                    'phone_number': invite.phone_number,
                    'email': invite.email,
                    'first_name': invite.first_name,
                    'last_name': invite.last_name,
                    'status': invite.status,
                    'expires_at': invite.expires_at,
                    'school_status': invite.school.status,
                },
            ).data,
        )


class SchoolAdminInviteAcceptView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(responses={200: SchoolAdminInviteAcceptResponseSerializer})
    def post(self, request, token):
        result = invite_services.accept_admin_invite(token=token)
        school = result['school']
        user = result['user']
        return Response(
            SchoolAdminInviteAcceptResponseSerializer(
                {
                    'message': (
                        'Invitation accepted. Sign in with your phone number to continue.'
                    ),
                    'school_id': school.id,
                    'school_name': school.name,
                    'phone_number': user.phone_number,
                    'created_user': result['created_user'],
                },
            ).data,
        )
