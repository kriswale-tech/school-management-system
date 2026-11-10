from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from platform_admin.serializers import PlatformPublicConfigSerializer
from platform_admin.services.settings import get_platform_settings


class PlatformPublicConfigView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(responses={200: PlatformPublicConfigSerializer})
    def get(self, request):
        settings_row = get_platform_settings()
        return Response(
            PlatformPublicConfigSerializer(
                {
                    'public_school_registration_enabled': (
                        settings_row.public_school_registration_enabled
                    ),
                },
            ).data,
        )
