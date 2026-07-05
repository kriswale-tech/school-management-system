from shared.constants import ghana_education_curriculum

GHANA_CURRICULUM_CODE = 'ghana'


def _save_level_content(level, data):
    from shared.models import CurriculumClassLevel, CurriculumSubject

    for index, class_name in enumerate(data['classes'], start=1):
        CurriculumClassLevel.objects.update_or_create(
            level=level,
            name=class_name,
            defaults={'order': index},
        )

    for index, subject_name in enumerate(data['subjects'], start=1):
        CurriculumSubject.objects.update_or_create(
            level=level,
            name=subject_name,
            defaults={'order': index},
        )


def _create_or_update_level(curriculum, name, parent, order, data):
    from shared.models import CurriculumLevel

    defaults = {'order': order}
    if 'description' in data:
        defaults['description'] = data['description']

    level, _ = CurriculumLevel.objects.update_or_create(
        curriculum=curriculum,
        parent=parent,
        name=name,
        defaults=defaults,
    )

    if 'classes' in data and 'subjects' in data:
        _save_level_content(level, data)
        return

    for index, (child_name, child_data) in enumerate(data.items(), start=1):
        _create_or_update_level(curriculum, child_name, level, index, child_data)


def seed_ghana_curriculum():
    """Bootstrap Ghana templates from constants (one-time / dev convenience)."""
    from shared.models import Curriculum

    curriculum, _ = Curriculum.objects.update_or_create(
        code=GHANA_CURRICULUM_CODE,
        defaults={'name': 'Ghana Education Curriculum', 'is_active': True},
    )

    for index, (name, data) in enumerate(ghana_education_curriculum.items(), start=1):
        _create_or_update_level(curriculum, name, None, index, data)

    return curriculum


def provision_school_curriculum(school, curriculum_code=GHANA_CURRICULUM_CODE):
    from academics.models import ClassLevel, ClassStream, ClassSubject, Level, Subject
    from shared.models import Curriculum, CurriculumLevel

    if Level.objects.filter(school=school).exists():
        return

    curriculum = Curriculum.objects.filter(code=curriculum_code, is_active=True).first()
    if not curriculum:
        seed_ghana_curriculum()
        curriculum = Curriculum.objects.get(code=curriculum_code)

    teachable_levels = (
        CurriculumLevel.objects.filter(
            curriculum=curriculum,
            class_levels__isnull=False,
        )
        .distinct()
        .order_by('order', 'name')
    )

    subject_cache = {}

    for level_template in teachable_levels:
        school_level = Level.objects.create(
            school=school,
            name=level_template.name,
            description=level_template.description,
            order=level_template.order,
        )

        class_level_map = {}
        for class_template in level_template.class_levels.all():
            class_level = ClassLevel.objects.create(
                level=school_level,
                name=class_template.name,
                description=level_template.description,
                order=class_template.order,
            )
            ClassStream.objects.create(class_level=class_level, is_default=True)
            class_level_map[class_template.id] = class_level

        for subject_template in level_template.subjects.all():
            subject = subject_cache.get(subject_template.name)
            if not subject:
                subject, _ = Subject.objects.get_or_create(
                    school=school,
                    name=subject_template.name,
                )
                subject_cache[subject_template.name] = subject

            for class_level in class_level_map.values():
                ClassSubject.objects.get_or_create(
                    school=school,
                    class_level=class_level,
                    subject=subject,
                )
