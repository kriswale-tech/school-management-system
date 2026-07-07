from django.core.exceptions import ValidationError
from django.db import transaction

from academics.models import ClassLevel, ClassSubject, ClassStream, Level, Subject


def create_custom_level(school, *, name, description=None, order=1):
    return Level.objects.create(
        school=school,
        name=name,
        description=description,
        order=order,
        subject_scope=Level.SubjectScope.CLASS,
        allows_custom_classes=True,
        is_system_generated=False,
    )


def create_custom_class_level(school, *, level, name, description=None, order=1):
    if level.school_id != school.id:
        raise ValidationError({'level': 'Must belong to the school.'})
    if not level.allows_custom_classes:
        raise ValidationError({'level': 'Custom classes are not allowed for this level.'})

    class_level = ClassLevel.objects.create(
        school=school,
        level=level,
        name=name,
        description=description,
        order=order,
        is_system_generated=False,
    )
    ClassStream.objects.create(class_level=class_level, is_default=True)
    return class_level


def create_custom_subject(school, *, name):
    return Subject.objects.create(
        school=school,
        name=name,
        is_system_generated=False,
    )


def assign_subject_to_class(school, *, class_level, subject):
    if class_level.school_id != school.id:
        raise ValidationError({'class_level': 'Must belong to the school.'})
    if subject.school_id != school.id:
        raise ValidationError({'subject': 'Must belong to the school.'})
    if not class_level.level.uses_per_class_subjects():
        raise ValidationError({
            'class_level': 'Subjects for this level are managed at level scope.',
        })

    assignment, _ = ClassSubject.objects.get_or_create(
        school=school,
        class_level=class_level,
        subject=subject,
        defaults={'is_system_generated': False},
    )
    return assignment


@transaction.atomic
def assign_custom_subject_to_level(school, *, level, subject):
    if level.school_id != school.id:
        raise ValidationError({'level': 'Must belong to the school.'})
    if subject.school_id != school.id:
        raise ValidationError({'subject': 'Must belong to the school.'})
    if level.uses_per_class_subjects():
        raise ValidationError({
            'level': 'Assign subjects directly to each class for this level.',
        })
    if subject.is_system_generated:
        raise ValidationError({'subject': 'System-generated subjects cannot be reassigned.'})

    class_levels = level.class_levels.all()
    if not class_levels.exists():
        raise ValidationError({'level': 'Add at least one class before assigning subjects.'})

    assignments = []
    for class_level in class_levels:
        assignment, _ = ClassSubject.objects.get_or_create(
            school=school,
            class_level=class_level,
            subject=subject,
            defaults={'is_system_generated': False},
        )
        assignments.append(assignment)
    return assignments


def remove_subject_from_class(school, *, class_level, subject):
    if class_level.school_id != school.id:
        raise ValidationError({'class_level': 'Must belong to the school.'})
    if not class_level.level.uses_per_class_subjects():
        raise ValidationError({
            'class_level': 'Subjects for this level are managed at level scope.',
        })

    assignment = ClassSubject.objects.filter(
        school=school,
        class_level=class_level,
        subject=subject,
        is_system_generated=False,
    ).first()
    if not assignment:
        raise ValidationError({'subject': 'Custom subject assignment not found.'})

    assignment.delete()


def delete_custom_level(level):
    if level.is_system_generated:
        raise ValidationError('System-generated levels cannot be deleted.')
    level.delete()


def delete_custom_class_level(class_level):
    if class_level.is_system_generated:
        raise ValidationError('System-generated classes cannot be deleted.')
    class_level.delete()


def delete_custom_subject(subject):
    if subject.is_system_generated:
        raise ValidationError('System-generated subjects cannot be deleted.')
    subject.delete()
