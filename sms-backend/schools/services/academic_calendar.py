"""School calendar for settings: list years, prepare the next one, switch term.

Signup still uses schools.services.academic.save_academic_year_setup, which
creates the first year and marks it active. This module never does that.
"""

from datetime import date

from django.db import transaction
from django.db.models import Exists, OuterRef
from rest_framework.exceptions import ValidationError

from assessments.models import StudentResult
from assessments.services.term_config import copy_forward_assessment_configs
from fees.models import FeeStructure
from schools.models import AcademicYear, Term
from schools.services.academic import TERM_ORDER
from students.models import ClassEnrollment

TERM_NAMES = {
    Term.TermChoices.FIRST_TERM: 'First Term',
    Term.TermChoices.SECOND_TERM: 'Second Term',
    Term.TermChoices.THIRD_TERM: 'Third Term',
}


def _label_start(label: str) -> int:
    return int(label.split('/')[0])


def next_year_label(label: str) -> str:
    end_year = int(label.split('/')[1])
    return f'{end_year}/{end_year + 1}'


def _latest_year(school):
    years = list(AcademicYear.objects.filter(school=school))
    if not years:
        return None
    return max(years, key=lambda year: _label_start(year.academic_year))


def _year_status(year, today):
    if year.is_active:
        return 'current'
    if year.end_date < today:
        return 'past'
    return 'upcoming'


def _terms_by_key(year):
    return {term.term: term for term in year.terms.all()}


def expected_next_term(active):
    year = active.academic_year
    if active.term == Term.TermChoices.FIRST_TERM:
        return year.terms.filter(term=Term.TermChoices.SECOND_TERM).first()
    if active.term == Term.TermChoices.SECOND_TERM:
        return year.terms.filter(term=Term.TermChoices.THIRD_TERM).first()

    following = AcademicYear.objects.filter(
        school_id=year.school_id,
        academic_year=next_year_label(year.academic_year),
    ).first()
    if following is None:
        return None
    return following.terms.filter(term=Term.TermChoices.FIRST_TERM).first()


def _unreleased_report_count(*, school, term) -> int:
    released = StudentResult.objects.filter(
        term_id=OuterRef('term_id'),
        student_id=OuterRef('student_id'),
        stream_id=OuterRef('stream_id'),
        status=StudentResult.Status.RELEASED,
    )
    return (
        ClassEnrollment.objects.filter(term=term, student__school=school)
        .exclude(Exists(released))
        .count()
    )


def _fee_warning(school, term) -> str | None:
    structure = FeeStructure.objects.filter(school=school, term=term).first()
    if structure is None:
        return 'This term has no fee catalog yet.'
    if structure.status != FeeStructure.Status.APPLIED:
        return "This term's fees have not been applied yet."
    return None


def list_academic_calendar(school, *, today=None):
    today = today or date.today()
    years = list(
        AcademicYear.objects.filter(school=school)
        .prefetch_related('terms')
        .order_by('start_date', 'academic_year')
    )
    active = (
        Term.objects.filter(school=school, is_active=True)
        .select_related('academic_year')
        .first()
    )
    expected = expected_next_term(active) if active else None
    latest = _latest_year(school)

    serialized_years = []
    for year in years:
        status = _year_status(year, today)
        stored = _terms_by_key(year)
        terms = []
        for term_key in TERM_ORDER:
            term = stored.get(term_key)
            is_ended = bool(term and term.end_date < today)
            can_edit = status == 'upcoming' or (status == 'current' and not is_ended)
            if status == 'past':
                can_edit = False
            terms.append({
                'id': term.id if term else None,
                'term': term_key,
                'name': TERM_NAMES[term_key],
                'start_date': term.start_date if term else None,
                'end_date': term.end_date if term else None,
                'is_active': bool(term and term.is_active),
                'is_ended': is_ended,
                'can_edit_dates': can_edit if term or status != 'past' else False,
                'is_next': bool(expected and term and term.id == expected.id and not term.is_active),
            })
        serialized_years.append({
            'id': year.id,
            'academic_year': year.academic_year,
            'start_date': year.start_date,
            'end_date': year.end_date,
            'is_active': year.is_active,
            'status': status,
            'terms': terms,
        })

    return {
        'years': serialized_years,
        'next_year_label': next_year_label(latest.academic_year) if latest else None,
        'active_term_id': active.id if active else None,
    }


def _neighbor_bounds(school, label):
    start_year = _label_start(label)
    previous = AcademicYear.objects.filter(
        school=school,
        academic_year=f'{start_year - 1}/{start_year}',
    ).first()
    following = AcademicYear.objects.filter(
        school=school,
        academic_year=f'{start_year + 1}/{start_year + 2}',
    ).first()
    return previous, following


def _validate_schedule(terms_by_key, label, *, previous=None, following=None, open_ended=False, today=None):
    today = today or date.today()
    first = terms_by_key[Term.TermChoices.FIRST_TERM]
    second = terms_by_key[Term.TermChoices.SECOND_TERM]
    third = terms_by_key[Term.TermChoices.THIRD_TERM]

    for term_key in TERM_ORDER:
        item = terms_by_key[term_key]
        if item['start_date'] >= item['end_date']:
            raise ValidationError({
                'terms': f'{TERM_NAMES[term_key]} must end after it starts.',
            })

    if first['end_date'] > second['start_date']:
        raise ValidationError({
            'terms': 'Second term must start on or after first term ends.',
        })
    if second['end_date'] > third['start_date']:
        raise ValidationError({
            'terms': 'Third term must start on or after second term ends.',
        })

    expected_label = f"{first['start_date'].year}/{third['end_date'].year}"
    if label != expected_label:
        raise ValidationError({
            'academic_year': f'Academic year must be {expected_label} based on term dates.',
        })

    if previous and first['start_date'] < previous.end_date:
        raise ValidationError({
            'terms': f'This year must start on or after {previous.academic_year} ends ({previous.end_date.isoformat()}).',
        })
    if following and third['end_date'] > following.start_date:
        raise ValidationError({
            'terms': f'This year must end on or before {following.academic_year} starts ({following.start_date.isoformat()}).',
        })
    if open_ended and third['end_date'] < today:
        raise ValidationError({
            'terms': 'A new academic year must end today or later.',
        })


def _terms_by_key_from_payload(terms):
    return {item['term']: item for item in terms}


def _apply_term_dates(school, year, terms_by_key):
    created_terms = []
    for term_key in TERM_ORDER:
        item = terms_by_key[term_key]
        term, created = Term.objects.update_or_create(
            academic_year=year,
            term=term_key,
            defaults={
                'school': school,
                'start_date': item['start_date'],
                'end_date': item['end_date'],
            },
        )
        if created:
            created_terms.append(term)

    first = terms_by_key[Term.TermChoices.FIRST_TERM]
    third = terms_by_key[Term.TermChoices.THIRD_TERM]
    year.start_date = first['start_date']
    year.end_date = third['end_date']
    year.save(update_fields=['start_date', 'end_date', 'updated_at'])

    for term in created_terms:
        copy_forward_assessment_configs(school=school, target_term=term)
    return created_terms


def create_next_academic_year(school, validated_data, *, today=None):
    today = today or date.today()
    latest = _latest_year(school)
    if latest is None:
        raise ValidationError({
            'academic_year': 'Finish school setup before adding another academic year.',
        })

    label = validated_data['academic_year']
    expected = next_year_label(latest.academic_year)
    if label != expected:
        raise ValidationError({
            'academic_year': f'The next academic year is {expected}.',
        })

    terms_by_key = _terms_by_key_from_payload(validated_data['terms'])
    _validate_schedule(
        terms_by_key,
        label,
        previous=latest,
        open_ended=True,
        today=today,
    )

    with transaction.atomic():
        year = AcademicYear.objects.create(
            school=school,
            academic_year=label,
            start_date=terms_by_key[Term.TermChoices.FIRST_TERM]['start_date'],
            end_date=terms_by_key[Term.TermChoices.THIRD_TERM]['end_date'],
            is_active=False,
        )
        _apply_term_dates(school, year, terms_by_key)

    return list_academic_calendar(school, today=today)


def update_academic_year_dates(school, year, validated_data, *, today=None):
    today = today or date.today()
    if year.school_id != school.id:
        raise ValidationError({'academic_year': 'Academic year not found for this school.'})

    label = validated_data['academic_year']
    if label != year.academic_year:
        raise ValidationError({
            'academic_year': f'This year stays {year.academic_year}. Add the next year to move forward.',
        })

    status = _year_status(year, today)
    if status == 'past':
        raise ValidationError({'academic_year': 'Past academic years are read-only.'})

    terms_by_key = _terms_by_key_from_payload(validated_data['terms'])
    stored = _terms_by_key(year)
    if status == 'current':
        for term_key in TERM_ORDER:
            existing = stored.get(term_key)
            incoming = terms_by_key[term_key]
            if existing and existing.end_date < today:
                if (
                    existing.start_date != incoming['start_date']
                    or existing.end_date != incoming['end_date']
                ):
                    raise ValidationError({
                        'terms': f'{TERM_NAMES[term_key]} has ended. Its dates stay as they are.',
                    })

    previous, following = _neighbor_bounds(school, label)
    _validate_schedule(terms_by_key, label, previous=previous, following=following, today=today)

    with transaction.atomic():
        _apply_term_dates(school, year, terms_by_key)

    return list_academic_calendar(school, today=today)


def preview_term_switch(school, term_id, *, today=None):
    today = today or date.today()
    target = (
        Term.objects.filter(school=school, id=term_id)
        .select_related('academic_year')
        .first()
    )
    if target is None:
        raise ValidationError({'term': 'Term not found in this school.'})

    active = (
        Term.objects.filter(school=school, is_active=True)
        .select_related('academic_year')
        .first()
    )
    blockers = []
    warnings = []
    label = f'{target.get_term_display()} {target.academic_year.academic_year}'

    if active is None:
        blockers.append('There is no current term to switch from.')
    elif target.id == active.id:
        blockers.append('This term is already the current term.')
    else:
        expected = expected_next_term(active)
        if expected is None:
            blockers.append('The next term is not set up yet.')
        elif expected.id != target.id:
            blockers.append(
                'You can only switch to '
                f'{expected.get_term_display()} ({expected.academic_year.academic_year}).'
            )
        else:
            if target.start_date < active.end_date:
                blockers.append('The next term must start on or after the current term ends.')
            else:
                if today < target.start_date:
                    warnings.append(
                        f'This term starts on {target.start_date.isoformat()}. Today is still before then.'
                    )
                fee_warning = _fee_warning(school, target)
                if fee_warning:
                    warnings.append(fee_warning)
                unreleased = _unreleased_report_count(school=school, term=active)
                if unreleased:
                    noun = 'report is' if unreleased == 1 else 'reports are'
                    warnings.append(f'{unreleased} {noun} still unreleased on the current term.')

    return {
        'can_switch': not blockers,
        'blockers': blockers,
        'warnings': warnings,
        'term_id': target.id,
        'term_label': label,
    }


def activate_term(school, term_id, *, acknowledge_warnings, today=None):
    preview = preview_term_switch(school, term_id, today=today)
    if preview['blockers']:
        raise ValidationError({'detail': ' '.join(preview['blockers'])})
    if preview['warnings'] and not acknowledge_warnings:
        raise ValidationError({'warnings': preview['warnings']})

    target = Term.objects.select_related('academic_year').get(school=school, id=term_id)
    with transaction.atomic():
        AcademicYear.objects.filter(school=school, is_active=True).update(is_active=False)
        Term.objects.filter(school=school, is_active=True).update(is_active=False)
        year = target.academic_year
        year.is_active = True
        year.save(update_fields=['is_active', 'updated_at'])
        target.is_active = True
        target.save(update_fields=['is_active', 'updated_at'])
        copy_forward_assessment_configs(school=school, target_term=target)

    return list_academic_calendar(school, today=today)
