from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from platform_admin.authentication import PlatformJWTCookieAuthentication
from platform_admin.models import PlatformUser
from platform_admin.permissions import IsPlatformAuthenticated
from platform_admin.serializers import PlatformSettingsSerializer
from platform_admin.services.audit import record_audit
from platform_admin.services.settings import get_platform_settings, update_platform_settings
from platform_admin.utils import client_ip


class PlatformSettingsView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(responses={200: PlatformSettingsSerializer})
    def get(self, request):
        return Response(PlatformSettingsSerializer(get_platform_settings()).data)

    @extend_schema(
        request=PlatformSettingsSerializer,
        responses={200: PlatformSettingsSerializer},
    )
    def patch(self, request):
        if request.platform_user.role != PlatformUser.Role.SUPER_ADMIN:
            return Response(
                {'detail': 'Only super admins can update platform settings.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = PlatformSettingsSerializer(
            get_platform_settings(),
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        updated = update_platform_settings(**serializer.validated_data)
        record_audit(
            actor=request.platform_user,
            action='platform.settings.updated',
            target_type='platform_settings',
            target_id=str(updated.pk),
            detail=serializer.validated_data,
            ip_address=client_ip(request),
        )
        return Response(PlatformSettingsSerializer(updated).data)
