import django_filters
from django.db.models import Q

from accounts.models import SchoolMembership, User


class SchoolMemberFilter(django_filters.FilterSet):
    """Filters memberships, so role and is_active mean 'in this school'."""

    role = django_filters.ChoiceFilter(choices=User.RoleChoices.choices)
    is_active = django_filters.BooleanFilter()
    exclude = django_filters.CharFilter(
        method='filter_exclude',
        help_text='Exclude one or more roles. Use comma-separated values, e.g. exclude=teacher,staff.',
    )
    search = django_filters.CharFilter(
        method='filter_search',
        help_text='Search first name, last name, email, or phone number.',
    )

    class Meta:
        model = SchoolMembership
        fields = ['role', 'is_active']

    def filter_exclude(self, queryset, name, value):
        valid_roles = {choice[0] for choice in User.RoleChoices.choices}
        roles = [
            role.strip()
            for role in value.split(',')
            if role.strip() in valid_roles
        ]
        if not roles:
            return queryset
        return queryset.exclude(role__in=roles)

    def filter_search(self, queryset, name, value):
        term = value.strip()
        if not term:
            return queryset

        return queryset.filter(
            Q(user__first_name__icontains=term)
            | Q(user__last_name__icontains=term)
            | Q(user__email__icontains=term)
            | Q(user__phone_number__icontains=term),
        )
