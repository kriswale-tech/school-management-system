import django_filters
from django.db.models import F, Q

from students.models import ClassEnrollment, Parent


class StudentEnrollmentFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(
        method='filter_search',
        help_text='Search student ID or full name.',
    )
    class_level = django_filters.UUIDFilter(field_name='class_level_id')
    stream = django_filters.UUIDFilter(field_name='stream_id')
    debtors = django_filters.BooleanFilter(
        method='filter_debtors',
        help_text='When true, only students with an outstanding balance.',
    )
    missing_guardian = django_filters.BooleanFilter(
        method='filter_missing_guardian',
        help_text='When true, only students with no linked guardian/parent.',
    )
    is_new_student = django_filters.BooleanFilter(
        field_name='is_new_student',
        help_text='When true, only new students for the active term.',
    )

    class Meta:
        model = ClassEnrollment
        fields = ['class_level', 'stream', 'debtors', 'missing_guardian', 'is_new_student']

    def filter_search(self, queryset, name, value):
        term = value.strip()
        if not term:
            return queryset

        return queryset.filter(student_text_search_q(term, prefix='student__'))

    def filter_debtors(self, queryset, name, value):
        if value is True:
            return queryset.filter(total_billed__gt=F('total_paid'))
        if value is False:
            return queryset.filter(total_billed__lte=F('total_paid'))
        return queryset

    def filter_missing_guardian(self, queryset, name, value):
        if value is True:
            return queryset.filter(has_guardian=False)
        if value is False:
            return queryset.filter(has_guardian=True)
        return queryset


def student_text_search_q(term, *, prefix=''):
    """Match a student ID, one name part, or every word of a full name."""
    term = (term or '').strip()
    if not term:
        return Q()

    def field(name):
        return f'{prefix}{name}'

    name_match = Q()
    for word in term.split():
        name_match &= (
            Q(**{f'{field("first_name")}__icontains': word})
            | Q(**{f'{field("last_name")}__icontains': word})
            | Q(**{f'{field("other_names")}__icontains': word})
        )

    return Q(**{f'{field("student_id")}__icontains': term}) | name_match


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
