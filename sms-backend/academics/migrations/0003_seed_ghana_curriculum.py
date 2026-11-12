from django.db import migrations


def seed_ghana_curriculum(apps, schema_editor):
    """Seed with the schema at this migration. Do not call the live service:
    later columns such as status do not exist yet when this runs."""
    from academics.curriculum_guard import allow_curriculum_writes

    Curriculum = apps.get_model('academics', 'Curriculum')
    CurriculumLevel = apps.get_model('academics', 'CurriculumLevel')
    CurriculumClassLevel = apps.get_model('academics', 'CurriculumClassLevel')
    CurriculumSubject = apps.get_model('academics', 'CurriculumSubject')

    with allow_curriculum_writes():
        _seed(Curriculum, CurriculumLevel, CurriculumClassLevel, CurriculumSubject)


def _seed(Curriculum, CurriculumLevel, CurriculumClassLevel, CurriculumSubject):
    from academics.constants.curriculum_constants import ghana_education_curriculum

    curriculum, _ = Curriculum.objects.update_or_create(
        code='ghana',
        version='2024',
        defaults={'name': 'Ghana Education Curriculum', 'is_active': True},
    )

    for name, data in ghana_education_curriculum.items():
        defaults = {}
        if 'description' in data:
            defaults['description'] = data['description']
        if 'subject_scope' in data:
            defaults['subject_scope'] = data['subject_scope']
        if 'allows_custom_classes' in data:
            defaults['allows_custom_classes'] = data['allows_custom_classes']
        if 'order' in data:
            defaults['order'] = data['order']
        level, _ = CurriculumLevel.objects.update_or_create(
            curriculum=curriculum,
            name=name,
            defaults=defaults,
        )
        if 'classes' not in data or 'subjects' not in data:
            continue
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
            continue
        for subject_name in subjects:
            CurriculumSubject.objects.update_or_create(
                level=level,
                name=subject_name,
                curriculum_class_level=None,
                defaults={},
            )


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0002_initial'),
    ]

    operations = [
        migrations.RunPython(seed_ghana_curriculum, migrations.RunPython.noop),
    ]
