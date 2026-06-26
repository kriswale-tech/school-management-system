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


def _step_value(step) -> str:
    return step.value if hasattr(step, 'value') else step


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


def advance_setup_step(school_setup: SchoolSetup, step: str) -> dict:
    step_value = _step_value(step)
    completed = list(school_setup.completed_steps or [])
    if step_value not in completed:
        completed.append(step_value)

    actionable_steps = [choice.value for choice in SETUP_STEP_ORDER]
    completed_count = len([item for item in completed if item in actionable_steps])
    progress = round((completed_count / len(actionable_steps)) * 100)
    is_complete = all(item in completed for item in actionable_steps)

    school_setup.completed_steps = completed
    school_setup.progress_percentage = progress

    if is_complete:
        school_setup.current_step = SchoolSetup.SetupStep.COMPLETED
        school_setup.completed_at = timezone.now()
        school = school_setup.school
        school.setup_completed = True
        school.setup_completed_at = timezone.now()
        school.save(update_fields=['setup_completed', 'setup_completed_at', 'updated_at'])
        next_step = SchoolSetup.SetupStep.COMPLETED
    else:
        next_step = next(item for item in actionable_steps if item not in completed)
        school_setup.current_step = next_step

    school_setup.save()

    return {
        'next_step': next_step,
        'completed_steps': completed,
        'is_complete': is_complete,
        'progress_percentage': progress,
    }
