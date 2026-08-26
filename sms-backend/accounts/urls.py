from django.urls import path

from accounts.views import (
    AdminSignUpView,
    AdminVerifyOtpView,
    CreateSchoolView,
    LoginVerifyOtpView,
    LoginView,
    LogoutView,
    MeView,
    RefreshTokenView,
    ResendLoginOtpView,
    ResendOtpView,
    SelectSchoolView,
    StaffDeskDetailView,
    StaffDeskListView,
    StaffDeskStatsView,
    UserDetailView,
    UserListCreateView,
)

urlpatterns = [
    path('me/', MeView.as_view(), name='me'),
    path('schools/', CreateSchoolView.as_view(), name='create-school'),
    path('select-school/', SelectSchoolView.as_view(), name='select-school'),
    path('signup/', AdminSignUpView.as_view(), name='admin-signup'),
    path('verify-otp/', AdminVerifyOtpView.as_view(), name='admin-verify-otp'),
    path('resend-otp/', ResendOtpView.as_view(), name='resend-otp'),
    path('login/', LoginView.as_view(), name='login'),
    path('login/verify-otp/', LoginVerifyOtpView.as_view(), name='login-verify-otp'),
    path('login/resend-otp/', ResendLoginOtpView.as_view(), name='login-resend-otp'),
    path('refresh/', RefreshTokenView.as_view(), name='refresh-token'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('users/', UserListCreateView.as_view(), name='user-list'),
    path('users/<uuid:pk>/', UserDetailView.as_view(), name='user-detail'),
    # Staff directory (separate from /users/ so existing user-management stays unchanged)
    path('staff/', StaffDeskListView.as_view(), name='staff-desk-list'),
    path('staff/stats/', StaffDeskStatsView.as_view(), name='staff-desk-stats'),
    path('staff/<uuid:pk>/', StaffDeskDetailView.as_view(), name='staff-desk-detail'),
]
