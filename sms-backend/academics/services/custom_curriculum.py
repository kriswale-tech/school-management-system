from django.core.exceptions import ValidationError
from django.db import models, transaction

from academics.models import (
    ClassLevel,
    ClassSubject,
    ClassStream,
    Level,
    LevelSubject,
    Subject,
    SubjectGroup,
)


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


@transaction.atomic
def create_custom_class_level(school, *, level, name, description=None, order=None):
    if level.school_id != school.id:
        raise ValidationError({'level': 'Must belong to the school.'})
    if not level.allows_custom_classes:
        raise ValidationError({'level': 'Custom classes are not allowed for this level.'})

    siblings = ClassLevel.objects.filter(level=level)
    if order is None:
        max_order = siblings.order_by('-order').values_list('order', flat=True).first()
        order = (max_order or 0) + 1
    else:
        siblings.filter(order__gte=order).update(order=models.F('order') + 1)

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


@transaction.atomic
def update_custom_class_level(class_level, *, name=None, description=None, order=None):
    if class_level.is_system_generated:
        raise ValidationError({'class_level': 'System-generated classes cannot be edited.'})

    if name is not None:
        class_level.name = name
    if description is not None:
        class_level.description = description
    if order is not None and order != class_level.order:
        siblings = ClassLevel.objects.filter(level_id=class_level.level_id).exclude(
            pk=class_level.pk,
        )
        old_order = class_level.order
        if order < old_order:
            siblings.filter(order__gte=order, order__lt=old_order).update(
                order=models.F('order') + 1,
            )
        else:
            siblings.filter(order__gt=old_order, order__lte=order).update(
                order=models.F('order') - 1,
            )
        class_level.order = order
    class_level.save()
    return class_level


def create_custom_subject(school, *, name):
    return Subject.objects.create(
        school=school,
        name=name,
        is_system_generated=False,
    )


def ensure_level_subject(school, *, level, subject):
    if level.school_id != school.id:
        raise ValidationError({'level': 'Must belong to the school.'})
    if subject.school_id != school.id:
        raise ValidationError({'subject': 'Must belong to the school.'})

    level_subject, _ = LevelSubject.objects.get_or_create(
        level=level,
        subject=subject,
        defaults={
            'school': school,
            'is_system_generated': False,
        },
    )
    return level_subject


def assign_subject_to_class(school, *, class_level, subject):
    if class_level.school_id != school.id:
        raise ValidationError({'class_level': 'Must belong to the school.'})
    if subject.school_id != school.id:
        raise ValidationError({'subject': 'Must belong to the school.'})
    if not class_level.level.uses_per_class_subjects():
        raise ValidationError({
            'class_level': 'Subjects for this level are managed at level scope.',
        })

    level_subject = LevelSubject.objects.filter(
        level=class_level.level,
        subject=subject,
    ).first()
    if not level_subject:
        raise ValidationError({'subject': 'Subject must belong to the level first.'})

    defaults = {'is_system_generated': False}
    if level_subject.is_system_generated and level_subject.curriculum_subject_id:
        defaults = {
            'is_system_generated': True,
            'curriculum_subject_id': level_subject.curriculum_subject_id,
        }
    else:
        template = (
            ClassSubject.objects.filter(
                school=school,
                subject=subject,
                curriculum_subject__isnull=False,
            )
            .exclude(class_level=class_level)
            .first()
        )
        if template:
            defaults = {
                'is_system_generated': True,
                'curriculum_subject_id': template.curriculum_subject_id,
            }

    assignment, _ = ClassSubject.objects.get_or_create(
        school=school,
        class_level=class_level,
        subject=subject,
        defaults=defaults,
    )
    return assignment


def assign_subject_to_class_strict(school, *, class_level, subject):
    """Assign subject to class; error if the assignment already exists."""
    if ClassSubject.objects.filter(
        school=school,
        class_level=class_level,
        subject=subject,
    ).exists():
        raise ValidationError({
            'subject': 'Subject is already assigned to this class.',
        })
    return assign_subject_to_class(school, class_level=class_level, subject=subject)


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

    ensure_level_subject(school, level=level, subject=subject)

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
    ).first()
    if not assignment:
        raise ValidationError({'subject': 'Subject assignment not found for this class.'})

    from academics.models import StudentSubjectGroup

    if StudentSubjectGroup.objects.filter(class_subject=assignment).exists():
        raise ValidationError({
            'subject': 'Cannot remove subject while students are assigned to its groups.',
        })

    assignment.delete()


def delete_custom_level(level):
    if level.is_system_generated:
        raise ValidationError('System-generated levels cannot be deleted.')
    level.delete()


def class_level_has_associations(class_level):
    from academics.models import StudentSubjectGroup

    if StudentSubjectGroup.objects.filter(class_subject__class_level=class_level).exists():
        return True
    return any(stream_has_associations(stream) for stream in class_level.streams.all())


def delete_custom_class_level(class_level):
    if class_level.is_system_generated:
        raise ValidationError('System-generated classes cannot be deleted.')
    if class_level_has_associations(class_level):
        raise ValidationError({
            'class_level': 'Cannot delete class while it has student associations.',
        })
    class_level.delete()


def delete_custom_subject(subject):
    if subject.is_system_generated:
        raise ValidationError('System-generated subjects cannot be deleted.')

    from academics.models import StudentSubjectGroup

    if StudentSubjectGroup.objects.filter(class_subject__subject=subject).exists():
        raise ValidationError({
            'subject': 'Cannot delete subject while students are assigned to its groups.',
        })
    subject.delete()


def stream_has_associations(stream):
    from students.models import ClassEnrollment

    return ClassEnrollment.objects.filter(stream=stream).exists()


def create_stream(school, *, class_level, name, description=None):
    if class_level.school_id != school.id:
        raise ValidationError({'class_level': 'Must belong to the school.'})
    if not name:
        raise ValidationError({'name': 'Required for non-default streams.'})

    return ClassStream.objects.create(
        class_level=class_level,
        name=name,
        description=description,
        is_default=False,
    )


def update_stream(stream, *, name=None, description=None, is_active=None):
    if stream.is_default and name:
        raise ValidationError({'name': 'Default streams should not have a name.'})
    if not stream.is_default and name is not None and not name:
        raise ValidationError({'name': 'Required for non-default streams.'})

    if name is not None and not stream.is_default:
        stream.name = name
    if description is not None:
        stream.description = description
    if is_active is not None:
        stream.is_active = is_active
    stream.save()
    return stream


def delete_stream(stream):
    if stream.is_default:
        raise ValidationError({'stream': 'The default stream cannot be deleted.'})
    if stream_has_associations(stream):
        raise ValidationError({
            'stream': 'Cannot delete stream while it has student associations.',
        })
    stream.delete()


def _class_subjects_for_level_subject(level, subject):
    return ClassSubject.objects.filter(
        class_level__level=level,
        subject=subject,
    ).select_related('class_level')


def _sibling_class_subjects(class_subject):
    return _class_subjects_for_level_subject(
        class_subject.class_level.level,
        class_subject.subject,
    )


@transaction.atomic
def create_subject_group(school, *, level, subject, name):
    if level.school_id != school.id:
        raise ValidationError({'level': 'Must belong to the school.'})
    if subject.school_id != school.id:
        raise ValidationError({'subject': 'Must belong to the school.'})
    if not LevelSubject.objects.filter(level=level, subject=subject).exists():
        raise ValidationError({'subject': 'Subject must belong to the level first.'})
    if not name:
        raise ValidationError({'name': 'This field is required.'})

    class_subjects = list(_class_subjects_for_level_subject(level, subject))
    if not class_subjects:
        raise ValidationError({
            'subject': 'Assign the subject to at least one class before adding groups.',
        })

    groups = []
    for target in class_subjects:
        group, _ = SubjectGroup.objects.get_or_create(
            class_subject=target,
            name=name,
            defaults={'is_active': True},
        )
        groups.append(group)

    return sorted(groups, key=lambda item: item.class_subject.class_level.name)[0]


@transaction.atomic
def update_subject_group(group, *, name=None, is_active=None):
    class_subject = group.class_subject
    siblings = SubjectGroup.objects.filter(
        class_subject__in=_sibling_class_subjects(class_subject),
        name=group.name,
    )

    for sibling in siblings:
        if name is not None:
            sibling.name = name
        if is_active is not None:
            sibling.is_active = is_active
        sibling.save()

    group.refresh_from_db()
    return group


@transaction.atomic
def delete_subject_group(group):
    class_subject = group.class_subject
    siblings = list(
        SubjectGroup.objects.filter(
            class_subject__in=_sibling_class_subjects(class_subject),
            name=group.name,
        ),
    )

    for sibling in siblings:
        if sibling.student_assignments.exists():
            raise ValidationError({
                'group': 'Cannot delete group while students are assigned to it.',
            })

    for sibling in siblings:
        sibling.delete()


@transaction.atomic
def create_subject_with_assignments(school, *, level, name, class_ids=None):
    if level.school_id != school.id:
        raise ValidationError({'level': 'Must belong to the school.'})

    subject = create_custom_subject(school, name=name)
    ensure_level_subject(school, level=level, subject=subject)

    if level.uses_per_class_subjects():
        class_ids = class_ids or []
        if class_ids:
            class_levels = list(
                ClassLevel.objects.filter(school=school, level=level, id__in=class_ids),
            )
            if len(class_levels) != len(set(class_ids)):
                raise ValidationError({
                    'class_ids': 'One or more classes do not belong to this level.',
                })
            for class_level in class_levels:
                assign_subject_to_class(school, class_level=class_level, subject=subject)
    else:
        if class_ids:
            raise ValidationError({
                'class_ids': 'Subjects for this level are assigned to all classes.',
            })
        assign_custom_subject_to_level(school, level=level, subject=subject)

    return subject


@transaction.atomic
def update_subject_with_assignments(school, *, subject, name=None, class_ids=None, level=None):
    if subject.school_id != school.id:
        raise ValidationError({'subject': 'Must belong to the school.'})

    if name is not None:
        if subject.is_system_generated:
            raise ValidationError({'name': 'System-generated subjects cannot be renamed.'})
        subject.name = name
        subject.save(update_fields=['name', 'updated_at'])

    if class_ids is None:
        return subject

    level_subjects = list(
        subject.level_subjects.select_related('level').filter(school=school),
    )
    assignments = list(
        subject.class_subjects.select_related('class_level__level').filter(school=school),
    )

    if level is None:
        if assignments:
            level = assignments[0].class_level.level
        elif level_subjects:
            if len({item.level_id for item in level_subjects}) > 1:
                raise ValidationError({
                    'subject': 'Subject belongs to multiple levels; cannot infer level.',
                })
            level = level_subjects[0].level
        else:
            raise ValidationError({'subject': 'Subject does not belong to any level.'})

    if level.school_id != school.id:
        raise ValidationError({'level': 'Must belong to the school.'})

    ensure_level_subject(school, level=level, subject=subject)

    if level.uses_per_class_subjects():
        desired_ids = set(class_ids)
        class_levels = list(
            ClassLevel.objects.filter(school=school, level=level, id__in=desired_ids),
        )
        if len(class_levels) != len(desired_ids):
            raise ValidationError({
                'class_ids': 'One or more classes do not belong to this level.',
            })

        current_ids = {
            item.class_level_id
            for item in assignments
            if item.class_level.level_id == level.id
        }
        for class_level in class_levels:
            if class_level.id not in current_ids:
                assign_subject_to_class(school, class_level=class_level, subject=subject)

        for assignment in assignments:
            if (
                assignment.class_level.level_id == level.id
                and assignment.class_level_id not in desired_ids
            ):
                remove_subject_from_class(
                    school,
                    class_level=assignment.class_level,
                    subject=subject,
                )
    else:
        if subject.is_system_generated:
            raise ValidationError({
                'subject': 'System-generated subjects cannot be reassigned at level scope.',
            })
        if class_ids:
            raise ValidationError({
                'class_ids': 'Subjects for this level are assigned to all classes.',
            })
        assign_custom_subject_to_level(school, level=level, subject=subject)

    return subject


def set_level_active(level, *, is_active):
    level.is_active = is_active
    level.save(update_fields=['is_active', 'updated_at'])
    return level


def set_class_level_active(class_level, *, is_active):
    class_level.is_active = is_active
    class_level.save(update_fields=['is_active', 'updated_at'])
    return class_level


def set_subject_active(subject, *, is_active):
    subject.is_active = is_active
    subject.save(update_fields=['is_active', 'updated_at'])
    return subject
