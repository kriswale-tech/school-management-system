from platform_admin.views.auth import (
    PlatformHelloView,
    PlatformLoginView,
    PlatformLogoutView,
    PlatformMeView,
    PlatformMfaDisableView,
    PlatformMfaSetupConfirmView,
    PlatformMfaSetupStartView,
    PlatformMfaVerifyView,
    PlatformRefreshView,
)
from platform_admin.views.invites import (
    PlatformSchoolInviteCreateView,
    PlatformSchoolInviteResendView,
)
from platform_admin.views.public import PlatformPublicConfigView
from platform_admin.views.schools import (
    PlatformSchoolDetailView,
    PlatformSchoolListCreateView,
    PlatformSchoolStatusView,
    PlatformSchoolSummaryView,
)
from platform_admin.views.settings import PlatformSettingsView

__all__ = [
    'PlatformHelloView',
    'PlatformLoginView',
    'PlatformLogoutView',
    'PlatformMeView',
    'PlatformMfaDisableView',
    'PlatformMfaSetupConfirmView',
    'PlatformMfaSetupStartView',
    'PlatformMfaVerifyView',
    'PlatformPublicConfigView',
    'PlatformRefreshView',
    'PlatformSchoolDetailView',
    'PlatformSchoolInviteCreateView',
    'PlatformSchoolInviteResendView',
    'PlatformSchoolListCreateView',
    'PlatformSchoolStatusView',
    'PlatformSchoolSummaryView',
    'PlatformSettingsView',
]
