from django.urls import path

from accounts.views import (
    AdminSignUpView,
    AdminVerifyOtpView,
    LoginVerifyOtpView,
    LoginView,
    LogoutView,
    MeView,
    RefreshTokenView,
    ResendLoginOtpView,
    ResendOtpView,
)

urlpatterns = [
    path('me/', MeView.as_view(), name='me'),
    path('signup/', AdminSignUpView.as_view(), name='admin-signup'),
    path('verify-otp/', AdminVerifyOtpView.as_view(), name='admin-verify-otp'),
    path('resend-otp/', ResendOtpView.as_view(), name='resend-otp'),
    path('login/', LoginView.as_view(), name='login'),
    path('login/verify-otp/', LoginVerifyOtpView.as_view(), name='login-verify-otp'),
    path('login/resend-otp/', ResendLoginOtpView.as_view(), name='login-resend-otp'),
    path('refresh/', RefreshTokenView.as_view(), name='refresh-token'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
