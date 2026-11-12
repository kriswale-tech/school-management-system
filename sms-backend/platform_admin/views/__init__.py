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
    PlatformSchoolAuditView,
    PlatformSchoolDetailView,
    PlatformSchoolListCreateView,
    PlatformSchoolStatusView,
    PlatformSchoolSummaryView,
)
from platform_admin.views.curriculum import (
    CurriculumDraftCreateView,
    CurriculumDraftView,
    CurriculumOverviewView,
    SchoolCurriculumAdoptionView,
)
from platform_admin.views.settings import PlatformSettingsView

__all__ = [
    'CurriculumDraftCreateView',
    'CurriculumDraftView',
    'CurriculumOverviewView',
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
    'PlatformSchoolAuditView',
    'PlatformSchoolDetailView',
    'PlatformSchoolInviteCreateView',
    'PlatformSchoolInviteResendView',
    'PlatformSchoolListCreateView',
    'PlatformSchoolStatusView',
    'PlatformSchoolSummaryView',
    'PlatformSettingsView',
    'SchoolCurriculumAdoptionView',
]
