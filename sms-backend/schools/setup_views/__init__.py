from schools.setup_views.academic_year_term import SetupAcademicYearTermView
from schools.setup_views.assessment import (
    CompleteAssessmentSetupView,
    SetupAssessmentLevelConfigView,
    SetupAssessmentView,
)
from schools.setup_views.fees import (
    CompleteFeesSetupView,
    SetupFeeItemCreateView,
    SetupFeeItemDetailView,
    SetupFeesView,
)
from schools.setup_views.classes_and_subjects import (
    CompleteClassesAndSubjectsSetupView,
    SetupClassStatusView,
    SetupClassStreamCreateView,
    SetupClassStreamDetailView,
    SetupClassSubjectAssignmentView,
    SetupClassesAndSubjectsView,
    SetupCustomClassCreateView,
    SetupCustomClassDetailView,
    SetupLevelStatusView,
    SetupSubjectCreateView,
    SetupSubjectDetailView,
    SetupSubjectGroupCreateView,
    SetupSubjectGroupDetailView,
    SetupSubjectStatusView,
)
from schools.setup_views.common import SchoolSetupView, advance_setup_if_needed
from schools.setup_views.school_profile import SetupSchoolProfileView

__all__ = [
    'CompleteAssessmentSetupView',
    'CompleteClassesAndSubjectsSetupView',
    'CompleteFeesSetupView',
    'SchoolSetupView',
    'SetupAcademicYearTermView',
    'SetupAssessmentLevelConfigView',
    'SetupAssessmentView',
    'SetupClassStatusView',
    'SetupClassStreamCreateView',
    'SetupClassStreamDetailView',
    'SetupClassSubjectAssignmentView',
    'SetupClassesAndSubjectsView',
    'SetupCustomClassCreateView',
    'SetupCustomClassDetailView',
    'SetupFeeItemCreateView',
    'SetupFeeItemDetailView',
    'SetupFeesView',
    'SetupLevelStatusView',
    'SetupSchoolProfileView',
    'SetupSubjectCreateView',
    'SetupSubjectDetailView',
    'SetupSubjectGroupCreateView',
    'SetupSubjectGroupDetailView',
    'SetupSubjectStatusView',
    'advance_setup_if_needed',
]
