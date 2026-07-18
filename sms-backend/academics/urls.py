from django.urls import path

from academics.views import ActiveClassLevelListView, ActiveLevelListView

urlpatterns = [
    path('levels/', ActiveLevelListView.as_view(), name='academics-levels'),
    path(
        'class-levels/',
        ActiveClassLevelListView.as_view(),
        name='academics-class-levels',
    ),
]
