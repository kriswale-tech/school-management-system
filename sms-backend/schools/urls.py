from django.urls import path

from schools.setup_views import (
    SchoolSetupView,
    SetupAcademicYearTermView,
    SetupSchoolProfileView,
)
from schools.views import SchoolView

urlpatterns = [
    path('setup/', SchoolSetupView.as_view(), name='school-setup'),
    path(
        'setup/school-profile/',
        SetupSchoolProfileView.as_view(),
        name='school-setup-profile',
    ),
    path(
        'setup/academic-year-term/',
        SetupAcademicYearTermView.as_view(),
        name='school-setup-academic-year-term',
    ),
    path('school/', SchoolView.as_view(), name='school'),
]
