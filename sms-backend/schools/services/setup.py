from django.utils import timezone

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


def advance_setup_step(school_setup: SchoolSetup, step: str) -> dict:
    completed = list(school_setup.completed_steps or [])
    if step not in completed:
        completed.append(step)

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
