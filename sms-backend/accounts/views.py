from django.conf import settings
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.cookies import clear_auth_cookies, set_auth_cookies
from accounts.filters import SchoolMemberFilter
from accounts.models import User
from accounts.permissions import CanManageUser, HasActiveSchool
from accounts.serializers import (
    AddUserSerializer,
    AdminSignUpSerializer,
    AdminVerifyOtpSerializer,
    AuthResponseSerializer,
    CreateSchoolSerializer,
    DeleteUserResponseSerializer,
    MessageResponseSerializer,
    ResendOtpSerializer,
    SchoolMembershipSerializer,
    SchoolMemberSerializer,
    SelectSchoolSerializer,
    UpdateUserResponseSerializer,
    UpdateUserSerializer,
    UserSerializer,
)
from accounts.services.memberships import (
    NO_SCHOOL_ACCESS_MESSAGE,
    active_memberships,
    get_active_membership,
    get_active_school,
    touch_membership,
)
from accounts.services.users import (
    get_school_membership,
    list_school_memberships,
    remove_school_member,
)
from accounts.tokens import blacklist_token, build_token
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


def _scoped_auth_response(
    request,
    user,
    membership,
    memberships,
    message,
    *,
    linked_existing_account=False,
):
    """Set auth cookies for a token that may or may not be scoped to a school."""
    if membership is not None:
        touch_membership(membership)

    refresh = build_token(user, membership)
    payload = {
        'message': message,
        'requires_school_selection': membership is None,
        'linked_existing_account': linked_existing_account,
        'active_school': membership,
        'schools': memberships,
    }
    response = Response(
        AuthResponseSerializer(payload).data,
        status=status.HTTP_200_OK,
    )
    set_auth_cookies(response, str(refresh.access_token), str(refresh))
    # forces the CSRF token to be set in the response
    get_token(request)
    return response


def _otp_auth_response(
    request,
    user,
    message='OTP verified successfully',
    *,
    preferred_membership=None,
    linked_existing_account=False,
):
    """Authenticate after OTP, scoping to the user's school when unambiguous.

    A user with a single school is logged straight in. A user with several gets
    an identity-only token and must call select-school before touching school
    data, so they can never act in a school they did not choose.

    preferred_membership overrides that when signup just created a school for a
    returning user — they should land in the school they asked for.
    """
    memberships = list(active_memberships(user))

    if not memberships:
        return Response(
            MessageResponseSerializer({'message': NO_SCHOOL_ACCESS_MESSAGE}).data,
            status=status.HTTP_403_FORBIDDEN,
        )

    if preferred_membership is not None:
        membership = preferred_membership
    elif len(memberships) == 1:
        membership = memberships[0]
    else:
        membership = None

    return _scoped_auth_response(
        request,
        user,
        membership,
        memberships,
        message,
        linked_existing_account=linked_existing_account,
    )


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
        description=(
            'Returns the authenticated user, the school the session is scoped to, '
            'and every school the user can act in. When requires_school_selection '
            'is true, call select-school/ before using school endpoints.'
        ),
        responses={200: UserSerializer},
    )
    def get(self, request):
        serializer = UserSerializer(
            request.user,
            context={
                'membership': request.membership,
                'memberships': list(active_memberships(request.user)),
            },
        )
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class AdminSignUpView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'admin_signup'

    @extend_schema(
        tags=['Accounts'],
        summary='Admin signup',
        description=(
            'Start creating a school. An OTP is sent to the phone number. '
            'New phones create a draft account; phones that already belong to a '
            'verified person stage the new school and create it after OTP verify. '
            'A person cannot create a second school with the same name they already '
            'administer.'
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
        result = serializer.save()
        send_signup_otp(result.user.phone_number)

        return Response(
            MessageResponseSerializer({
                'message': 'OTP sent successfully',
                'linked_existing_account': result.linked_existing_account,
            }).data,
            status=status.HTTP_201_CREATED,
        )


class CreateSchoolView(APIView):
    @extend_schema(
        tags=['Accounts'],
        summary='Create an additional school',
        description=(
            'Lets an already-verified user start another school, which they will '
            'administer. No OTP is required because the phone number is already '
            'verified. Call select-school/ afterwards to switch into it.'
        ),
        request=CreateSchoolSerializer,
        responses={
            201: SchoolMembershipSerializer,
            400: OpenApiResponse(description='Validation error'),
        },
    )
    def post(self, request):
        serializer = CreateSchoolSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()
        return Response(
            SchoolMembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )


class SelectSchoolView(APIView):
    @extend_schema(
        tags=['Accounts'],
        summary='Select or switch school',
        description=(
            'Scopes the session to one of the user\'s schools and re-issues the '
            'auth cookies. Used both for the initial choice after login and for '
            'switching schools later. The previous refresh token is retired.'
        ),
        request=SelectSchoolSerializer,
        responses={
            200: AuthResponseSerializer,
            400: OpenApiResponse(description='Validation error'),
            403: OpenApiResponse(description='No access to this school'),
        },
    )
    def post(self, request):
        serializer = SelectSchoolSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        membership = get_active_membership(
            request.user,
            serializer.validated_data['school_id'],
        )
        if membership is None:
            raise PermissionDenied('You do not have access to this school.')

        blacklist_token(request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH']))

        return _scoped_auth_response(
            request,
            request.user,
            membership,
            list(active_memberships(request.user)),
            f'Switched to {membership.school.name}',
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
            'Verify the OTP sent during admin signup. On success, activates a new '
            'account or creates the staged school for a returning user, then sets '
            'HttpOnly auth cookies scoped to that school.'
        ),
        request=AdminVerifyOtpSerializer,
        responses={
            200: AuthResponseSerializer,
            400: MessageResponseSerializer,
        },
    )
    def post(self, request):
        serializer = AdminVerifyOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = verify_signup_otp(
                serializer.validated_data['phone_number'],
                serializer.validated_data['otp'],
            )
        except OtpVerificationError as exc:
            return Response(
                MessageResponseSerializer({'message': str(exc)}).data,
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValidationError as exc:
            detail = exc.detail
            if isinstance(detail, dict):
                first = next(iter(detail.values()))
                message = first[0] if isinstance(first, list) else first
            else:
                message = detail
            return Response(
                MessageResponseSerializer({'message': str(message)}).data,
                status=status.HTTP_400_BAD_REQUEST,
            )

        message = (
            'Welcome back — your new school is ready'
            if result.linked_existing_account
            else 'OTP verified successfully'
        )
        return _otp_auth_response(
            request,
            result.user,
            message=message,
            preferred_membership=result.membership,
            linked_existing_account=result.linked_existing_account,
        )


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
            'Verify the OTP sent during login and set HttpOnly auth cookies. '
            'Users belonging to a single school are scoped to it immediately; '
            'users belonging to several must then call select-school/.'
        ),
        request=AdminVerifyOtpSerializer,
        responses={
            200: AuthResponseSerializer,
            400: MessageResponseSerializer,
            403: MessageResponseSerializer,
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
        description=(
            'Issues a new access token using the refresh token cookie. '
            'The selected school is carried over from the refresh token.'
        ),
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
        blacklist_token(request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH']))

        response = Response(
            MessageResponseSerializer({'message': 'Logged out'}).data,
            status=status.HTTP_200_OK,
        )
        clear_auth_cookies(response)
        return response


class UserListCreateView(APIView):
    permission_classes = [HasActiveSchool, CanManageUser]
    pagination_class = StandardResultsSetPagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        tags=['Accounts'],
        summary='List users',
        description=(
            'Returns paginated members of the selected school that the requester '
            'can manage. Admins see all roles; staff see teachers only. '
            'role and is_active describe the membership in this school, not the '
            'person\'s access elsewhere.'
        ),
        parameters=[
            OpenApiParameter(
                name='role',
                type=str,
                enum=[choice[0] for choice in User.RoleChoices.choices],
                description='Filter by role in this school.',
            ),
            OpenApiParameter(
                name='is_active',
                type=bool,
                description='Filter by active status in this school.',
            ),
            OpenApiParameter(
                name='exclude',
                type=str,
                description='Exclude role(s), comma-separated (e.g. teacher,staff).',
            ),
            OpenApiParameter(
                name='search',
                type=str,
                description='Search first name, last name, email, or phone number.',
            ),
            OpenApiParameter(name='page', type=int, description='Page number.'),
            OpenApiParameter(name='page_size', type=int, description='Page size (max 100).'),
        ],
        responses={
            200: paginated_schema(SchoolMemberSerializer, name='PaginatedUserList'),
        },
    )
    def get(self, request):
        queryset = list_school_memberships(request.membership)
        filterset = SchoolMemberFilter(request.query_params, queryset=queryset)
        if not filterset.is_valid():
            raise ValidationError(filterset.errors)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = SchoolMemberSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        tags=['Accounts'],
        summary='Add user',
        description=(
            'Add someone to the selected school. Admins can add any role; staff '
            'can add teachers only. When the phone number already belongs to a '
            'person in the system, that identity is reused and their existing '
            'name, email, and profile are kept. Send multipart/form-data when '
            'including an optional profile_picture file.'
        ),
        request=AddUserSerializer,
        responses={
            201: SchoolMemberSerializer,
            400: OpenApiResponse(description='Validation error'),
            403: OpenApiResponse(description='Permission denied'),
        },
    )
    def post(self, request):
        serializer = AddUserSerializer(
            data=request.data,
            context={'request': request, 'school': get_active_school(request)},
        )
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()
        return Response(
            SchoolMemberSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )


class UserDetailView(APIView):
    permission_classes = [HasActiveSchool, CanManageUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_membership(self, request, pk):
        membership = get_school_membership(get_active_school(request), pk)
        self.check_object_permissions(request, membership)
        return membership

    @extend_schema(
        tags=['Accounts'],
        summary='Get user',
        description='Returns a member of the selected school.',
        responses={
            200: SchoolMemberSerializer,
            404: OpenApiResponse(description='User not found'),
        },
    )
    def get(self, request, pk):
        membership = self.get_membership(request, pk)
        return Response(SchoolMemberSerializer(membership).data)

    @extend_schema(
        tags=['Accounts'],
        summary='Update user',
        description=(
            'Partially update a member of the selected school. Admins can update '
            'any manageable member; staff can update teachers only. While school '
            'setup is incomplete, admins may correct a member\'s phone number; if '
            'the corrected number already belongs to someone in the system, that '
            'person is linked to this school instead, linked_existing_user is true, '
            'and the returned user id changes. Send multipart/form-data when '
            'updating profile_picture.'
        ),
        request=UpdateUserSerializer,
        responses={
            200: UpdateUserResponseSerializer,
            400: OpenApiResponse(description='Validation error'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='User not found'),
        },
    )
    def patch(self, request, pk):
        membership = self.get_membership(request, pk)
        serializer = UpdateUserSerializer(
            membership,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(
            UpdateUserResponseSerializer({
                'user': result.membership,
                'linked_existing_user': result.linked_existing_user,
            }).data,
        )

    @extend_schema(
        tags=['Accounts'],
        summary='Remove user from school',
        description=(
            'Revokes the member\'s access to this school only; their access to '
            'other schools is untouched. While school setup is incomplete the '
            'membership is deleted outright, and the person record is removed too '
            'if they belong to no other school. Otherwise the membership is '
            'deactivated.'
        ),
        responses={
            200: DeleteUserResponseSerializer,
            400: OpenApiResponse(description='Validation error'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='User not found'),
        },
    )
    def delete(self, request, pk):
        membership = self.get_membership(request, pk)
        result = remove_school_member(request.membership, membership)
        response_data = {
            'hard_deleted': result.hard_deleted,
            'user': None if result.hard_deleted else result.membership,
        }
        return Response(
            DeleteUserResponseSerializer(response_data).data,
            status=status.HTTP_200_OK,
        )
