from django.urls import path

from activities.views import ActivityListView

urlpatterns = [
    path('', ActivityListView.as_view(), name='activity-list'),
]
