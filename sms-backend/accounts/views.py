from django.conf import settings
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.cookies import clear_auth_cookies, set_auth_cookies
from accounts.helpers import save_user_serializer
from accounts.permissions import CanManageUser
from accounts.serializers import (
    AddUserSerializer,
    AdminSignUpSerializer,
    AdminVerifyOtpSerializer,
    DeleteUserResponseSerializer,
    MessageResponseSerializer,
    ResendOtpSerializer,
    UpdateUserSerializer,
    UserSerializer,
)
from accounts.services.users import delete_user, get_school_user, list_school_users
from core.pagination import StandardResultsSetPagination, paginated_schema
from accounts.services.otp import (
    OtpResendCooldownError,
    OtpResendError,
    OtpSendError,
    OtpVerificationError,
    resend_login_otp,
    resend_signup_otp,
    send_login_otp,
    send_signup_otp,
    verify_login_otp,
    verify_signup_otp,
)


def _otp_auth_response(request, user, message='OTP verified successfully'):
    refresh = RefreshToken.for_user(user)
    response = Response(
        MessageResponseSerializer({'message': message}).data,
        status=status.HTTP_200_OK,
    )
    set_auth_cookies(response, str(refresh.access_token), str(refresh))
    get_token(request)
    return response


def _resend_otp_response(resend_fn, phone_number):
    try:
        resend_fn(phone_number)
    except OtpResendCooldownError as exc:
        return Response(
            MessageResponseSerializer({
                'message': str(exc),
                'retry_after_seconds': exc.retry_after_seconds,
            }).data,
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    except OtpResendError as exc:
        return Response(
            MessageResponseSerializer({'message': str(exc)}).data,
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        MessageResponseSerializer({'message': 'OTP sent successfully'}).data,
        status=status.HTTP_200_OK,
    )


class MeView(APIView):
    @extend_schema(
        tags=['Accounts'],
        summary='Get current user',
        description='Returns the authenticated user profile.',
        responses={200: UserSerializer},
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data)


@method_decorator(csrf_exempt, name='dispatch')
class AdminSignUpView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'admin_signup'

    @extend_schema(
        tags=['Accounts'],
        summary='Admin signup',
        description=(
            'Register a new school admin account. '
            'An OTP is sent to the provided phone number for verification.'
        ),
        request=AdminSignUpSerializer,
        responses={
            201: MessageResponseSerializer,
            400: OpenApiResponse(description='Validation error'),
        },
    )
    def post(self, request):
        serializer = AdminSignUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_signup_otp(user.phone_number)

        return Response(
            MessageResponseSerializer({'message': 'OTP sent successfully'}).data,
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_exempt, name='dispatch')
class AdminVerifyOtpView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'otp_verify'

    @extend_schema(
        tags=['Accounts'],
        summary='Verify admin OTP',
        description=(
            'Verify the OTP sent during admin signup. '
            'On success, activates the account and sets HttpOnly auth cookies.'
        ),
        request=AdminVerifyOtpSerializer,
        responses={
            200: MessageResponseSerializer,
            400: MessageResponseSerializer,
        },
    )
    def post(self, request):
        serializer = AdminVerifyOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = verify_signup_otp(
                serializer.validated_data['phone_number'],
                serializer.validated_data['otp'],
            )
        except OtpVerificationError as exc:
            return Response(
                MessageResponseSerializer({'message': str(exc)}).data,
                status=status.HTTP_400_BAD_REQUEST,
            )

        return _otp_auth_response(request, user)


@method_decorator(csrf_exempt, name='dispatch')
class ResendOtpView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'otp_send'

    @extend_schema(
        tags=['Accounts'],
        summary='Resend admin signup OTP',
        description=(
            'Resend the OTP for an inactive admin signup. '
            'Issues a new code and resets the expiry window and attempt count.'
        ),
        request=ResendOtpSerializer,
        responses={
            200: MessageResponseSerializer,
            400: MessageResponseSerializer,
            429: MessageResponseSerializer,
        },
    )
    def post(self, request):
        serializer = ResendOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return _resend_otp_response(
            resend_signup_otp,
            serializer.validated_data['phone_number'],
        )


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'otp_send'

    @extend_schema(
        tags=['Accounts'],
        summary='Request login OTP',
        description=(
            'Send an OTP to an active account phone number for login. '
            'Use login/verify-otp/ to complete authentication.'
        ),
        request=ResendOtpSerializer,
        responses={
            200: MessageResponseSerializer,
            400: MessageResponseSerializer,
        },
    )
    def post(self, request):
        serializer = ResendOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            send_login_otp(serializer.validated_data['phone_number'])
        except OtpSendError as exc:
            return Response(
                MessageResponseSerializer({'message': str(exc)}).data,
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            MessageResponseSerializer({'message': 'OTP sent successfully'}).data,
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_exempt, name='dispatch')
class LoginVerifyOtpView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'otp_verify'

    @extend_schema(
        tags=['Accounts'],
        summary='Verify login OTP',
        description=(
            'Verify the OTP sent during login. '
            'On success, sets HttpOnly auth cookies for the active account.'
        ),
        request=AdminVerifyOtpSerializer,
        responses={
            200: MessageResponseSerializer,
            400: MessageResponseSerializer,
        },
    )
    def post(self, request):
        serializer = AdminVerifyOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = verify_login_otp(
                serializer.validated_data['phone_number'],
                serializer.validated_data['otp'],
            )
        except OtpVerificationError as exc:
            return Response(
                MessageResponseSerializer({'message': str(exc)}).data,
                status=status.HTTP_400_BAD_REQUEST,
            )

        return _otp_auth_response(request, user, message='Logged in successfully')


@method_decorator(csrf_exempt, name='dispatch')
class ResendLoginOtpView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'otp_send'

    @extend_schema(
        tags=['Accounts'],
        summary='Resend login OTP',
        description=(
            'Resend the OTP for an active account login. '
            'Issues a new code and resets the expiry window and attempt count.'
        ),
        request=ResendOtpSerializer,
        responses={
            200: MessageResponseSerializer,
            400: MessageResponseSerializer,
            429: MessageResponseSerializer,
        },
    )
    def post(self, request):
        serializer = ResendOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return _resend_otp_response(
            resend_login_otp,
            serializer.validated_data['phone_number'],
        )


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=['Accounts'],
        summary='Refresh access token',
        description='Issues a new access token using the refresh token cookie.',
        responses={
            200: MessageResponseSerializer,
            401: MessageResponseSerializer,
        },
    )
    def post(self, request):
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'])
        if not refresh_token:
            return Response(
                MessageResponseSerializer({'message': 'Refresh token missing'}).data,
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            refresh = RefreshToken(refresh_token)
            access = refresh.access_token
        except TokenError:
            response = Response(
                MessageResponseSerializer({'message': 'Invalid refresh token'}).data,
                status=status.HTTP_401_UNAUTHORIZED,
            )
            clear_auth_cookies(response)
            return response

        response = Response(
            MessageResponseSerializer({'message': 'Token refreshed'}).data,
            status=status.HTTP_200_OK,
        )
        set_auth_cookies(response, str(access), str(refresh))
        # forces the CSRF token to be set in the response
        get_token(request)
        return response


class LogoutView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=['Accounts'],
        summary='Logout',
        description=(
            'Blacklists the refresh token when valid and always clears auth cookies. '
            'Does not require a valid access token.'
        ),
        responses={200: MessageResponseSerializer},
    )
    def post(self, request):
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'])
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass

        response = Response(
            MessageResponseSerializer({'message': 'Logged out'}).data,
            status=status.HTTP_200_OK,
        )
        clear_auth_cookies(response)
        return response


class UserListCreateView(APIView):
    permission_classes = [CanManageUser]
    pagination_class = StandardResultsSetPagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        tags=['Accounts'],
        summary='List users',
        description=(
            'Returns paginated users in the current school that the requester can manage. '
            'Admins see all roles; staff see teachers only.'
        ),
        responses={
            200: paginated_schema(UserSerializer, name='PaginatedUserList'),
        },
    )
    def get(self, request):
        role = request.query_params.get('role')
        is_active_param = request.query_params.get('is_active')
        is_active = None
        if is_active_param is not None:
            is_active = is_active_param.lower() in ('true', '1', 'yes')

        users = list_school_users(
            request.user,
            role=role,
            is_active=is_active,
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(users, request)
        serializer = UserSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        tags=['Accounts'],
        summary='Add user',
        description=(
            'Create a user in the current school. Admins can add any role; '
            'staff can add teachers only. Send multipart/form-data when '
            'including an optional profile_picture file.'
        ),
        request=AddUserSerializer,
        responses={
            201: UserSerializer,
            400: OpenApiResponse(description='Validation error'),
            403: OpenApiResponse(description='Permission denied'),
        },
    )
    def post(self, request):
        serializer = AddUserSerializer(
            data=request.data,
            context={'request': request, 'school': request.user.school},
        )
        serializer.is_valid(raise_exception=True)
        user = save_user_serializer(serializer)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class UserDetailView(APIView):
    permission_classes = [CanManageUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_user(self, request, pk):
        user = get_school_user(request.user.school, pk)
        self.check_object_permissions(request, user)
        return user

    @extend_schema(
        tags=['Accounts'],
        summary='Get user',
        description='Returns a user in the current school.',
        responses={
            200: UserSerializer,
            404: OpenApiResponse(description='User not found'),
        },
    )
    def get(self, request, pk):
        user = self.get_user(request, pk)
        return Response(UserSerializer(user).data)

    @extend_schema(
        tags=['Accounts'],
        summary='Update user',
        description=(
            'Partially update a user in the current school. Admins can update any '
            'manageable user; staff can update teachers only. During incomplete '
            'school setup, admins may also change a user\'s primary phone number. '
            'Send multipart/form-data when updating profile_picture.'
        ),
        request=UpdateUserSerializer,
        responses={
            200: UserSerializer,
            400: OpenApiResponse(description='Validation error'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='User not found'),
        },
    )
    def patch(self, request, pk):
        user = self.get_user(request, pk)
        serializer = UpdateUserSerializer(
            user,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        user = save_user_serializer(serializer)
        return Response(UserSerializer(user).data)

    @extend_schema(
        tags=['Accounts'],
        summary='Delete user',
        description=(
            'Removes a user when school setup is incomplete. After setup is '
            'complete, or when linked records prevent deletion, the user is '
            'deactivated instead.'
        ),
        responses={
            200: DeleteUserResponseSerializer,
            400: OpenApiResponse(description='Validation error'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='User not found'),
        },
    )
    def delete(self, request, pk):
        user = self.get_user(request, pk)
        result = delete_user(request.user, user)
        response_data = {
            'hard_deleted': result.hard_deleted,
            'user': None if result.hard_deleted else UserSerializer(result.user).data,
        }
        return Response(
            DeleteUserResponseSerializer(response_data).data,
            status=status.HTTP_200_OK,
        )