from django.urls import path

from accounts.views import AdminSignUpView, AdminVerifyOtpView, MeView

urlpatterns = [
    path('me/', MeView.as_view(), name='me'),
    path('signup/', AdminSignUpView.as_view(), name='admin-signup'),
    path('verify-otp/', AdminVerifyOtpView.as_view(), name='admin-verify-otp'),
]
