from django.db import transaction

from schools.models import AcademicYear, Term

TERM_ORDER = [
    Term.TermChoices.FIRST_TERM,
    Term.TermChoices.SECOND_TERM,
    Term.TermChoices.THIRD_TERM,
]


def _serialize_term(term):
    return {
        'term': term.term,
        'name': term.get_term_display(),
        'start_date': term.start_date,
        'end_date': term.end_date,
        'is_active': term.is_active,
    }


def get_academic_year_setup(school):
    academic_year = (
        AcademicYear.objects.filter(school=school, is_active=True)
        .prefetch_related('terms')
        .first()
    )
    if not academic_year:
        return {
            'academic_year': None,
            'start_date': None,
            'end_date': None,
            'is_active': False,
            'current_term': None,
            'terms': [],
        }

    terms = list(academic_year.terms.all())
    terms.sort(key=lambda item: TERM_ORDER.index(item.term))
    active_term = next((term for term in terms if term.is_active), None)

    return {
        'academic_year': academic_year.academic_year,
        'start_date': academic_year.start_date,
        'end_date': academic_year.end_date,
        'is_active': academic_year.is_active,
        'current_term': active_term.term if active_term else None,
        'terms': [_serialize_term(term) for term in terms],
    }


def save_academic_year_setup(school, validated_data):
    terms_by_key = {item['term']: item for item in validated_data['terms']}
    first_term = terms_by_key[Term.TermChoices.FIRST_TERM]
    third_term = terms_by_key[Term.TermChoices.THIRD_TERM]
    current_term = validated_data['current_term']

    with transaction.atomic():
        AcademicYear.objects.filter(school=school, is_active=True).update(is_active=False)
        Term.objects.filter(academic_year__school=school, is_active=True).update(is_active=False)

        academic_year, _ = AcademicYear.objects.update_or_create(
            school=school,
            academic_year=validated_data['academic_year'],
            defaults={
                'start_date': first_term['start_date'],
                'end_date': third_term['end_date'],
                'is_active': True,
            },
        )

        for term_key in TERM_ORDER:
            term_data = terms_by_key[term_key]
            Term.objects.update_or_create(
                academic_year=academic_year,
                term=term_key,
                defaults={
                    'school': school,
                    'start_date': term_data['start_date'],
                    'end_date': term_data['end_date'],
                    'is_active': term_key == current_term,
                },
            )

    return get_academic_year_setup(school)
