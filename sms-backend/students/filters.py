import django_filters
from django.db.models import F, Q

from students.models import ClassEnrollment, Parent


class StudentEnrollmentFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(
        method='filter_search',
        help_text='Search student ID, first name, last name, or other names.',
    )
    class_level = django_filters.UUIDFilter(field_name='class_level_id')
    stream = django_filters.UUIDFilter(field_name='stream_id')
    debtors = django_filters.BooleanFilter(
        method='filter_debtors',
        help_text='When true, only students with an outstanding balance.',
    )

    class Meta:
        model = ClassEnrollment
        fields = ['class_level', 'stream', 'debtors']

    def filter_search(self, queryset, name, value):
        term = value.strip()
        if not term:
            return queryset

        return queryset.filter(
            Q(student__student_id__icontains=term)
            | Q(student__first_name__icontains=term)
            | Q(student__last_name__icontains=term)
            | Q(student__other_names__icontains=term),
        )

    def filter_debtors(self, queryset, name, value):
        if value is True:
            return queryset.filter(total_billed__gt=F('total_paid'))
        if value is False:
            return queryset.filter(total_billed__lte=F('total_paid'))
        return queryset


class ParentFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(
        method='filter_search',
        help_text='Search parent name, phone number, or email.',
    )

    class Meta:
        model = Parent
        fields = []

    def filter_search(self, queryset, name, value):
        term = value.strip()
        if not term:
            return queryset

        return queryset.filter(
            Q(name__icontains=term)
            | Q(phone_number__icontains=term)
            | Q(email__icontains=term),
        )
