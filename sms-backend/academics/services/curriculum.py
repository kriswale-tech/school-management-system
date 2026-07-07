from academics.constants.curriculum_constants import ghana_education_curriculum
from academics.curriculum_guard import allow_curriculum_writes

GHANA_CURRICULUM_CODE = 'ghana'
GHANA_CURRICULUM_VERSION = '2024'


def _level_defaults(data):
    defaults = {}
    if 'description' in data:
        defaults['description'] = data['description']
    if 'subject_scope' in data:
        defaults['subject_scope'] = data['subject_scope']
    if 'allows_custom_classes' in data:
        defaults['allows_custom_classes'] = data['allows_custom_classes']
    if 'order' in data:
        defaults['order'] = data['order']
    return defaults


def _save_level_content(level, data):
    from academics.models import CurriculumClassLevel, CurriculumSubject

    class_templates = {}
    for index, class_name in enumerate(data['classes'], start=1):
        class_template, _ = CurriculumClassLevel.objects.update_or_create(
            level=level,
            name=class_name,
            defaults={'order': index},
        )
        class_templates[class_name] = class_template

    subjects = data['subjects']
    if isinstance(subjects, dict):
        for class_name, subject_names in subjects.items():
            class_template = class_templates[class_name]
            for subject_name in subject_names:
                CurriculumSubject.objects.update_or_create(
                    curriculum_class_level=class_template,
                    name=subject_name,
                    defaults={'level': level},
                )
        return

    for subject_name in subjects:
        CurriculumSubject.objects.update_or_create(
            level=level,
            name=subject_name,
            curriculum_class_level=None,
            defaults={},
        )


def seed_ghana_curriculum(version=GHANA_CURRICULUM_VERSION):
    """Bootstrap Ghana templates from constants (migration / platform seed only)."""
    from academics.models import Curriculum, CurriculumLevel

    with allow_curriculum_writes():
        curriculum, _ = Curriculum.objects.update_or_create(
            code=GHANA_CURRICULUM_CODE,
            version=version,
            defaults={'name': 'Ghana Education Curriculum', 'is_active': True},
        )

        for name, data in ghana_education_curriculum.items():
            level, _ = CurriculumLevel.objects.update_or_create(
                curriculum=curriculum,
                name=name,
                defaults=_level_defaults(data),
            )
            if 'classes' in data and 'subjects' in data:
                _save_level_content(level, data)

    return curriculum


def get_active_curriculum(curriculum_code=GHANA_CURRICULUM_CODE):
    from academics.models import Curriculum

    curriculum = (
        Curriculum.objects.filter(code=curriculum_code, is_active=True)
        .order_by('-version')
        .first()
    )
    if curriculum:
        return curriculum

    return seed_ghana_curriculum()


def _provision_level_content(school, school_level, level_template, subject_cache):
    from academics.models import ClassLevel, ClassStream, ClassSubject, Subject

    class_level_map = {}
    for class_template in level_template.class_levels.all():
        class_level = ClassLevel.objects.create(
            level=school_level,
            curriculum_class_level=class_template,
            name=class_template.name,
            description=level_template.description,
            order=class_template.order,
            is_system_generated=True,
        )
        ClassStream.objects.create(class_level=class_level, is_default=True)
        class_level_map[class_template.id] = class_level

    for subject_template in level_template.subjects.select_related('curriculum_class_level'):
        subject = subject_cache.get(subject_template.name)
        if not subject:
            subject, _ = Subject.objects.get_or_create(
                school=school,
                name=subject_template.name,
                defaults={'is_system_generated': True},
            )
            subject_cache[subject_template.name] = subject

        if subject_template.curriculum_class_level_id:
            target_class_levels = [
                class_level_map[subject_template.curriculum_class_level_id],
            ]
        else:
            target_class_levels = class_level_map.values()

        for class_level in target_class_levels:
            ClassSubject.objects.get_or_create(
                school=school,
                class_level=class_level,
                subject=subject,
                defaults={
                    'curriculum_subject': subject_template,
                    'is_system_generated': True,
                },
            )


def provision_school_curriculum(school, curriculum_code=GHANA_CURRICULUM_CODE):
    from academics.models import CurriculumLevel, Level

    if Level.objects.filter(school=school).exists():
        return

    curriculum = get_active_curriculum(curriculum_code)

    level_templates = (
        CurriculumLevel.objects.filter(curriculum=curriculum)
        .prefetch_related('class_levels', 'subjects__curriculum_class_level')
        .order_by('order', 'name')
    )

    subject_cache = {}

    for level_template in level_templates:
        school_level = Level.objects.create(
            school=school,
            curriculum_level=level_template,
            name=level_template.name,
            description=level_template.description,
            order=level_template.order,
            subject_scope=level_template.subject_scope,
            allows_custom_classes=level_template.allows_custom_classes,
            is_system_generated=True,
        )

        if level_template.class_levels.exists():
            _provision_level_content(school, school_level, level_template, subject_cache)

    school.provisioned_curriculum = curriculum
    school.save(update_fields=['provisioned_curriculum'])
