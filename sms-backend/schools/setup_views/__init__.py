from schools.setup_views.academic_year_term import SetupAcademicYearTermView
from schools.setup_views.classes_and_subjects import SetupClassesAndSubjectsView
from schools.setup_views.common import SchoolSetupView, advance_setup_if_needed
from schools.setup_views.school_profile import SetupSchoolProfileView

__all__ = [
    'SchoolSetupView',
    'SetupAcademicYearTermView',
    'SetupClassesAndSubjectsView',
    'SetupSchoolProfileView',
    'advance_setup_if_needed',
]
