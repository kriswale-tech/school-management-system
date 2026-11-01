from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response

from accounts.permissions import HasActiveSchool
from core.pagination import StandardResultsSetPagination, paginated_schema
from notifications.serializers import (
    MarkAllReadSerializer,
    NotificationSerializer,
    UnreadCountSerializer,
)
from notifications.services.inbox import (
    list_notifications,
    mark_all_read,
    mark_notification_read,
    unread_count,
)
from shared.views import SchoolScopedAPIView


class NotificationListView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool]
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        tags=['Notifications'],
        summary='List my in-app notifications',
        description=(
            'Newest-first personal inbox for the active school membership. '
            'Distinct from school alerts (live digests) and the activity feed.'
        ),
        parameters=[
            OpenApiParameter(
                name='unread',
                type=bool,
                description='If true, only unread notifications.',
            ),
            OpenApiParameter(name='page', type=int),
            OpenApiParameter(name='page_size', type=int),
        ],
        responses={200: paginated_schema(NotificationSerializer, name='PaginatedNotifications')},
    )
    def get(self, request):
        unread_only = str(request.query_params.get('unread', '')).lower() in {
            '1',
            'true',
            'yes',
        }
        queryset = list_notifications(
            membership=self.membership,
            unread_only=unread_only,
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(
            NotificationSerializer(page, many=True).data,
        )


class NotificationUnreadCountView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool]

    @extend_schema(
        tags=['Notifications'],
        summary='Unread notification count',
        responses={200: UnreadCountSerializer},
    )
    def get(self, request):
        return Response({'count': unread_count(membership=self.membership)})


class NotificationMarkReadView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool]

    @extend_schema(
        tags=['Notifications'],
        summary='Mark one notification as read',
        responses={200: NotificationSerializer},
    )
    def post(self, request, notification_id):
        notification = mark_notification_read(
            membership=self.membership,
            notification_id=notification_id,
        )
        return Response(NotificationSerializer(notification).data)


class NotificationMarkAllReadView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool]

    @extend_schema(
        tags=['Notifications'],
        summary='Mark all notifications as read',
        responses={200: MarkAllReadSerializer},
    )
    def post(self, request):
        updated = mark_all_read(membership=self.membership)
        return Response({'updated': updated})
