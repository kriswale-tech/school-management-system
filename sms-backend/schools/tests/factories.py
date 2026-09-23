from datetime import date, timedelta

from schools.models import AcademicYear, SchoolSetup, Term


def create_school_setup(
    school,
    *,
    completed_steps=None,
    current_step=SchoolSetup.SetupStep.SCHOOL_PROFILE,
):
    return SchoolSetup.objects.create(
        school=school,
        completed_steps=completed_steps or [],
        current_step=current_step,
    )


def academic_year_term_payload(**overrides):
    data = {
        'academic_year': '2026/2027',
        'current_term': 'first_term',
        'terms': [
            {
                'term': 'first_term',
                'start_date': '2026-09-01',
                'end_date': '2026-12-15',
            },
            {
                'term': 'second_term',
                'start_date': '2026-12-15',
                'end_date': '2027-04-01',
            },
            {
                'term': 'third_term',
                'start_date': '2027-04-01',
                'end_date': '2027-07-31',
            },
        ],
    }
    data.update(overrides)
    return data


def create_active_term(school, **overrides):
    today = date.today()
    start = overrides.pop('start_date', today - timedelta(days=30))
    end = overrides.pop('end_date', today + timedelta(days=60))
    year = AcademicYear.objects.create(
        school=school,
        academic_year=overrides.pop('academic_year', '2025/2026'),
        start_date=overrides.pop('year_start', start),
        end_date=overrides.pop('year_end', end),
        is_active=True,
    )
    return Term.objects.create(
        school=school,
        academic_year=year,
        term=overrides.pop('term', Term.TermChoices.FIRST_TERM),
        start_date=start,
        end_date=end,
        is_active=True,
        **overrides,
    )
