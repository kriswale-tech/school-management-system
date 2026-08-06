from django.urls import path

from academics.views import (
    ActiveClassLevelListView,
    ActiveLevelListView,
    AllClassesView,
    ClassDetailView,
    ClassListView,
    ClassStatsView,
    ClassStudentsView,
    ClassSubjectTeacherAssignView,
    ClassSubjectsView,
    ClassTeacherAssignView,
    ClassTeacherOptionsView,
)

urlpatterns = [
    path('levels/', ActiveLevelListView.as_view(), name='academics-levels'),
    path(
        'levels/all-classes/',
        AllClassesView.as_view(),
        name='academics-levels-all-classes',
    ),
    path(
        'class-levels/',
        ActiveClassLevelListView.as_view(),
        name='academics-class-levels',
    ),
    path('classes/stats/', ClassStatsView.as_view(), name='academics-classes-stats'),
    path(
        'classes/teachers/',
        ClassTeacherOptionsView.as_view(),
        name='academics-classes-teachers',
    ),
    path('classes/', ClassListView.as_view(), name='academics-classes'),
    path(
        'classes/<uuid:stream_id>/',
        ClassDetailView.as_view(),
        name='academics-class-detail',
    ),
    path(
        'classes/<uuid:stream_id>/students/',
        ClassStudentsView.as_view(),
        name='academics-class-students',
    ),
    path(
        'classes/<uuid:stream_id>/subjects/',
        ClassSubjectsView.as_view(),
        name='academics-class-subjects',
    ),
    path(
        'classes/<uuid:stream_id>/class-teacher/',
        ClassTeacherAssignView.as_view(),
        name='academics-class-teacher-assign',
    ),
    path(
        'classes/<uuid:stream_id>/subject-teacher/',
        ClassSubjectTeacherAssignView.as_view(),
        name='academics-class-subject-teacher-assign',
    ),
]
