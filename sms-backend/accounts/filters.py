import django_filters

from accounts.models import User


class UserFilter(django_filters.FilterSet):
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
        model = User
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

        from django.db.models import Q

        return queryset.filter(
            Q(first_name__icontains=term)
            | Q(last_name__icontains=term)
            | Q(email__icontains=term)
            | Q(phone_number__icontains=term),
        )
