from schools.models import SchoolSetup


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
