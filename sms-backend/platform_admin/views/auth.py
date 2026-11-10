from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from platform_admin.authentication import (
    PlatformJWTCookieAuthentication,
    PlatformMfaPendingAuthentication,
)
from platform_admin.cookies import clear_platform_auth_cookies, set_platform_auth_cookies
from platform_admin.models import PlatformUser
from platform_admin.permissions import IsPlatformAuthenticated
from platform_admin.serializers import (
    PlatformHelloSerializer,
    PlatformLoginSerializer,
    PlatformMfaSetupConfirmSerializer,
    PlatformMfaVerifySerializer,
    PlatformUserSerializer,
)
from platform_admin.services import auth as auth_services
from platform_admin.services.audit import record_audit
from platform_admin.tokens import (
    MFA_PENDING_CLAIM,
    PLATFORM_REALM,
    REALM_CLAIM,
    blacklist_platform_token,
    build_platform_token,
)
from platform_admin.utils import client_ip


def _auth_response(user: PlatformUser, access, refresh, *, status_code=status.HTTP_200_OK):
    response = Response(
        {
            'user': PlatformUserSerializer(user).data,
            'mfa_required': False,
        },
        status=status_code,
    )
    set_platform_auth_cookies(response, str(access), str(refresh))
    return response


class PlatformHelloView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [AllowAny]

    @extend_schema(responses={200: PlatformHelloSerializer})
    def get(self, request):
        user = getattr(request, 'platform_user', None)
        if user is None and isinstance(request.user, PlatformUser):
            user = request.user
        payload = {
            'name': 'SCHOOLASST Platform API',
            'version': '0.1.0',
            'authenticated': bool(user),
            'user': user,
        }
        return Response(PlatformHelloSerializer(payload).data)


class PlatformLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(request=PlatformLoginSerializer)
    def post(self, request):
        serializer = PlatformLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = auth_services.authenticate_platform_password(
                serializer.validated_data['email'],
                serializer.validated_data['password'],
            )
        except AuthenticationFailed as exc:
            return Response(
                {
                    'success': False,
                    'error_code': 'AUTHENTICATION_FAILED',
                    'detail': str(exc.detail),
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        result = auth_services.begin_login(user)
        record_audit(
            actor=user,
            action='platform.auth.login_password',
            target_type='platform_user',
            target_id=str(user.pk),
            detail={'mfa_required': result['mfa_required']},
            ip_address=client_ip(request),
        )
        if result['mfa_required']:
            return Response(
                {
                    'mfa_required': True,
                    'mfa_token': result['mfa_token'],
                    'user': PlatformUserSerializer(user).data,
                },
            )
        return _auth_response(user, result['access'], result['refresh'])


class PlatformMfaVerifyView(APIView):
    authentication_classes = [PlatformMfaPendingAuthentication]
    permission_classes = [AllowAny]

    @extend_schema(request=PlatformMfaVerifySerializer)
    def post(self, request):
        user = getattr(request, 'platform_user', None)
        if user is None:
            raw = request.data.get('mfa_token')
            if not raw:
                raise AuthenticationFailed('MFA session required.')
            try:
                token = AccessToken(raw)
            except TokenError as exc:
                raise AuthenticationFailed('Invalid or expired MFA session.') from exc
            if token.get(REALM_CLAIM) != PLATFORM_REALM or not token.get(MFA_PENDING_CLAIM):
                raise AuthenticationFailed('Invalid MFA session.')
            try:
                user = PlatformUser.objects.get(pk=token['user_id'], is_active=True)
            except PlatformUser.DoesNotExist as exc:
                raise AuthenticationFailed('User not found.') from exc

        serializer = PlatformMfaVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = auth_services.verify_login_mfa(user, serializer.validated_data['code'])
        record_audit(
            actor=user,
            action='platform.auth.login_mfa',
            target_type='platform_user',
            target_id=str(user.pk),
            ip_address=client_ip(request),
        )
        return _auth_response(user, result['access'], result['refresh'])


class PlatformRefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw = request.COOKIES.get(settings.PLATFORM_JWT['AUTH_COOKIE_REFRESH'])
        if not raw:
            raise AuthenticationFailed('Refresh token required.')
        try:
            refresh = RefreshToken(raw)
        except TokenError as exc:
            raise InvalidToken('Invalid refresh token.') from exc

        if refresh.get(REALM_CLAIM) != PLATFORM_REALM:
            raise InvalidToken('Invalid refresh token realm.')
        if refresh.get(MFA_PENDING_CLAIM):
            raise InvalidToken('Invalid refresh token.')

        try:
            user = PlatformUser.objects.get(pk=refresh['user_id'], is_active=True)
        except PlatformUser.DoesNotExist as exc:
            raise InvalidToken('User not found.') from exc

        blacklist_platform_token(raw)
        new_refresh = build_platform_token(user)
        return _auth_response(user, new_refresh.access_token, new_refresh)


class PlatformLogoutView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        user = getattr(request, 'platform_user', None)
        raw = request.COOKIES.get(settings.PLATFORM_JWT['AUTH_COOKIE_REFRESH'])
        blacklist_platform_token(raw)
        if user:
            record_audit(
                actor=user,
                action='platform.auth.logout',
                target_type='platform_user',
                target_id=str(user.pk),
                ip_address=client_ip(request),
            )
        response = Response({'detail': 'Logged out.'})
        clear_platform_auth_cookies(response)
        return response


class PlatformMeView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(responses={200: PlatformUserSerializer})
    def get(self, request):
        return Response(PlatformUserSerializer(request.platform_user).data)


class PlatformMfaSetupStartView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    def post(self, request):
        payload = auth_services.provision_mfa_secret(request.platform_user)
        return Response(payload)


class PlatformMfaSetupConfirmView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(request=PlatformMfaSetupConfirmSerializer)
    def post(self, request):
        serializer = PlatformMfaSetupConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = auth_services.confirm_mfa_setup(
            request.platform_user,
            serializer.validated_data['code'],
        )
        return Response(PlatformUserSerializer(user).data)


class PlatformMfaDisableView(APIView):
    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]

    @extend_schema(request=PlatformMfaVerifySerializer)
    def post(self, request):
        serializer = PlatformMfaVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = auth_services.disable_mfa(
            request.platform_user,
            serializer.validated_data['code'],
        )
        return Response(PlatformUserSerializer(user).data)
