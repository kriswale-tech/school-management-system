from django.urls import path

from academics.views import (
    ActiveClassLevelListView,
    ActiveLevelListView,
    AllClassesView,
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
]
