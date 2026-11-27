from datetime import datetime

from django.db.models import Q
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from core.pagination import StandardResultsSetPagination
from platform_admin.authentication import PlatformJWTCookieAuthentication
from platform_admin.models import PlatformAuditLog
from platform_admin.permissions import IsPlatformAuthenticated
from platform_admin.serializers.audit import PlatformAuditLogSerializer, schools_for_entries


def _parse_date(value: str, field: str):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError as exc:
        raise ValidationError({field: 'Use a YYYY-MM-DD date.'}) from exc


class PlatformAuditListView(APIView):
    """Read-only list of every platform audit entry."""

    authentication_classes = [PlatformJWTCookieAuthentication]
    permission_classes = [IsPlatformAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        params = request.query_params
        queryset = PlatformAuditLog.objects.select_related('actor')

        query = (params.get('q') or '').strip()
        if query:
            queryset = queryset.filter(
                Q(action__icontains=query)
                | Q(target_id__icontains=query)
                | Q(actor__email__icontains=query)
                | Q(actor__first_name__icontains=query)
                | Q(actor__last_name__icontains=query)
            )

        action = (params.get('action') or '').strip()
        if action:
            queryset = queryset.filter(action__startswith=action)

        target_type = (params.get('target_type') or '').strip()
        if target_type:
            queryset = queryset.filter(target_type=target_type)

        start = (params.get('start') or '').strip()
        end = (params.get('end') or '').strip()
        if start:
            queryset = queryset.filter(created_at__date__gte=_parse_date(start, 'start'))
        if end:
            queryset = queryset.filter(created_at__date__lte=_parse_date(end, 'end'))

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset.order_by('-created_at'), request, view=self)
        serializer = PlatformAuditLogSerializer(
            page,
            many=True,
            context={'schools': schools_for_entries(page or [])},
        )
        return paginator.get_paginated_response(serializer.data)
