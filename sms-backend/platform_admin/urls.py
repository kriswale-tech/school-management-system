from django.urls import path

from platform_admin.views import (
    PlatformHelloView,
    PlatformLoginView,
    PlatformLogoutView,
    PlatformMeView,
    PlatformMfaDisableView,
    PlatformMfaSetupConfirmView,
    PlatformMfaSetupStartView,
    PlatformMfaVerifyView,
    PlatformPublicConfigView,
    PlatformRefreshView,
    PlatformSchoolDetailView,
    PlatformSchoolInviteCreateView,
    PlatformSchoolInviteResendView,
    PlatformSchoolListCreateView,
    PlatformSchoolStatusView,
    PlatformSchoolSummaryView,
    PlatformSettingsView,
)

urlpatterns = [
    path('hello/', PlatformHelloView.as_view(), name='platform-hello'),
    path('public-config/', PlatformPublicConfigView.as_view(), name='platform-public-config'),
    path('auth/login/', PlatformLoginView.as_view(), name='platform-login'),
    path('auth/mfa/verify/', PlatformMfaVerifyView.as_view(), name='platform-mfa-verify'),
    path('auth/refresh/', PlatformRefreshView.as_view(), name='platform-refresh'),
    path('auth/logout/', PlatformLogoutView.as_view(), name='platform-logout'),
    path('auth/me/', PlatformMeView.as_view(), name='platform-me'),
    path('auth/mfa/setup/', PlatformMfaSetupStartView.as_view(), name='platform-mfa-setup'),
    path(
        'auth/mfa/setup/confirm/',
        PlatformMfaSetupConfirmView.as_view(),
        name='platform-mfa-setup-confirm',
    ),
    path('auth/mfa/disable/', PlatformMfaDisableView.as_view(), name='platform-mfa-disable'),
    path('settings/', PlatformSettingsView.as_view(), name='platform-settings'),
    path('schools/', PlatformSchoolListCreateView.as_view(), name='platform-school-list'),
    path(
        'schools/summary/',
        PlatformSchoolSummaryView.as_view(),
        name='platform-school-summary',
    ),
    path('schools/<uuid:pk>/', PlatformSchoolDetailView.as_view(), name='platform-school-detail'),
    path(
        'schools/<uuid:pk>/status/',
        PlatformSchoolStatusView.as_view(),
        name='platform-school-status',
    ),
    path(
        'schools/<uuid:pk>/invites/',
        PlatformSchoolInviteCreateView.as_view(),
        name='platform-school-invite-create',
    ),
    path(
        'schools/<uuid:pk>/invites/<uuid:invite_id>/resend/',
        PlatformSchoolInviteResendView.as_view(),
        name='platform-school-invite-resend',
    ),
]
