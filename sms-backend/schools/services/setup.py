from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from schools.models import SchoolSetup

SETUP_STEP_ORDER = [
    SchoolSetup.SetupStep.SCHOOL_PROFILE,
    SchoolSetup.SetupStep.ACADEMIC_YEAR_TERM,
    SchoolSetup.SetupStep.CLASSES_AND_SUBJECTS,
    SchoolSetup.SetupStep.ASSESSMENT,
    SchoolSetup.SetupStep.FEES,
    SchoolSetup.SetupStep.TEACHERS,
    SchoolSetup.SetupStep.STAFF,
]

REQUIRED_SETUP_STEPS = [
    SchoolSetup.SetupStep.SCHOOL_PROFILE,
    SchoolSetup.SetupStep.ACADEMIC_YEAR_TERM,
    SchoolSetup.SetupStep.CLASSES_AND_SUBJECTS,
    SchoolSetup.SetupStep.ASSESSMENT,
    SchoolSetup.SetupStep.FEES,
    SchoolSetup.SetupStep.TEACHERS,
]

OPTIONAL_SETUP_STEPS = [
    SchoolSetup.SetupStep.STAFF,
]


def _step_value(step) -> str:
    return step.value if hasattr(step, 'value') else step


OPTIONAL_SETUP_STEP_VALUES = {_step_value(step) for step in OPTIONAL_SETUP_STEPS}


def _required_step_values() -> list[str]:
    return [_step_value(step) for step in REQUIRED_SETUP_STEPS]


def _navigable_step_values() -> list[str]:
    return [_step_value(step) for step in SETUP_STEP_ORDER]


def _is_setup_finalized(school_setup: SchoolSetup) -> bool:
    return school_setup.school.setup_completed


def _build_setup_response(
    school_setup: SchoolSetup,
    *,
    next_step=None,
    completed_steps=None,
) -> dict:
    return {
        'next_step': next_step if next_step is not None else school_setup.current_step,
        'completed_steps': (
            completed_steps
            if completed_steps is not None
            else school_setup.completed_steps
        ),
        'is_complete': _is_setup_finalized(school_setup),
        'progress_percentage': school_setup.progress_percentage,
    }


def require_prior_setup_steps(school_setup: SchoolSetup, step) -> None:
    try:
        step_index = SETUP_STEP_ORDER.index(step)
    except ValueError:
        return

    completed = set(school_setup.completed_steps or [])
    for prior_step in SETUP_STEP_ORDER[:step_index]:
        if _step_value(prior_step) not in completed:
            raise ValidationError({
                'detail': f'Complete the "{prior_step.label}" step before continuing.',
            })


def advance_setup_if_needed(school_setup: SchoolSetup, step) -> dict:
    step_value = _step_value(step)
    if step_value not in (school_setup.completed_steps or []):
        return advance_setup_step(school_setup, step)

    return _build_setup_response(school_setup)


def _resolve_next_step(completed: list[str]) -> str:
    required_values = _required_step_values()
    navigable_values = _navigable_step_values()

    pending = [item for item in navigable_values if item not in completed]
    if pending:
        return pending[0]

    if all(item in completed for item in required_values):
        return SchoolSetup.SetupStep.STAFF

    return next(item for item in navigable_values if item not in completed)


def advance_setup_step(school_setup: SchoolSetup, step: str) -> dict:
    step_value = _step_value(step)
    completed = list(school_setup.completed_steps or [])
    if step_value not in completed:
        completed.append(step_value)

    required_values = _required_step_values()
    completed_required_count = len([
        item for item in completed if item in required_values
    ])
    progress = round((completed_required_count / len(required_values)) * 100)

    school_setup.completed_steps = completed
    school_setup.progress_percentage = progress
    next_step = (
        SchoolSetup.SetupStep.COMPLETED
        if _is_setup_finalized(school_setup)
        else _resolve_next_step(completed)
    )
    school_setup.current_step = next_step
    school_setup.save()

    return _build_setup_response(
        school_setup,
        next_step=next_step,
        completed_steps=completed,
    )


def validate_setup_ready(school, school_setup: SchoolSetup) -> None:
    completed = set(school_setup.completed_steps or [])
    missing_steps = [
        step_value
        for step_value in _required_step_values()
        if step_value not in completed
    ]
    if missing_steps:
        raise ValidationError({
            'detail': 'Complete all required setup steps before finishing setup.',
            'missing_steps': missing_steps,
        })

    if not school.name or not school.phone_number:
        raise ValidationError({'detail': 'School profile is incomplete.'})

    from schools.models import Term

    if not Term.objects.filter(school=school, is_active=True).exists():
        raise ValidationError({'detail': 'Set an active term before finishing setup.'})

    from schools.services.assessment import validate_assessment_setup_ready
    from schools.services.classes_and_subjects import validate_classes_and_subjects_ready
    from schools.services.fees import validate_fees_setup_ready
    from schools.services.teachers import validate_teachers_setup_ready

    validate_classes_and_subjects_ready(school)
    validate_assessment_setup_ready(school)
    validate_fees_setup_ready(school)
    validate_teachers_setup_ready(school)


def complete_school_setup(school) -> dict:
    school_setup, _ = SchoolSetup.objects.get_or_create(school=school)

    if school.setup_completed:
        raise ValidationError({'detail': 'School setup is already complete.'})

    validate_setup_ready(school, school_setup)

    from schools.services.fees import apply_active_term_fees

    with transaction.atomic():
        apply_active_term_fees(school)

        school_setup.current_step = SchoolSetup.SetupStep.COMPLETED
        school_setup.completed_at = timezone.now()
        school_setup.progress_percentage = 100
        school_setup.save()

        school.setup_completed = True
        school.setup_completed_at = timezone.now()
        school.save(update_fields=['setup_completed', 'setup_completed_at', 'updated_at'])

    return {
        'next_step': SchoolSetup.SetupStep.COMPLETED,
        'completed_steps': school_setup.completed_steps,
        'is_complete': True,
        'progress_percentage': 100,
    }
