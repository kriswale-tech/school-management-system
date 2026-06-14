from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse

from accounts.serializers import (
    AdminSignUpSerializer,
    AdminVerifyOtpSerializer,
    MessageResponseSerializer,
    TokenResponseSerializer,
    UserSerializer,
)
from accounts.services.otp import OtpVerificationError, send_signup_otp, verify_signup_otp


class MeView(APIView):
    @extend_schema(
        tags=['Accounts'],
        summary='Get current user',
        description='Returns the authenticated user profile.',
        responses={200: UserSerializer},
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data)


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

        response = MessageResponseSerializer({'message': 'OTP sent successfully'})
        return Response(response.data, status=status.HTTP_201_CREATED)


class AdminVerifyOtpView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'otp_verify'

    @extend_schema(
        tags=['Accounts'],
        summary='Verify admin OTP',
        description=(
            'Verify the OTP sent during admin signup. '
            'On success, activates the account and returns JWT tokens.'
        ),
        request=AdminVerifyOtpSerializer,
        responses={
            200: TokenResponseSerializer,
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
            response = MessageResponseSerializer({'message': str(exc)})
            return Response(response.data, status=status.HTTP_400_BAD_REQUEST)

        refresh = RefreshToken.for_user(user)
        response = TokenResponseSerializer({
            'message': 'OTP verified successfully',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })
        return Response(response.data, status=status.HTTP_200_OK)
