from django.db import migrations, models


def populate_parent_name(apps, schema_editor):
    Parent = apps.get_model('students', 'Parent')
    for parent in Parent.objects.all():
        parts = [
            parent.first_name.strip(),
            parent.other_names.strip() if parent.other_names else '',
            parent.last_name.strip(),
        ]
        parent.name = ' '.join(part for part in parts if part)
        parent.save(update_fields=['name'])


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0004_parent_and_student_parent'),
    ]

    operations = [
        migrations.AddField(
            model_name='parent',
            name='name',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.RunPython(populate_parent_name, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='parent',
            name='first_name',
        ),
        migrations.RemoveField(
            model_name='parent',
            name='last_name',
        ),
        migrations.RemoveField(
            model_name='parent',
            name='other_names',
        ),
        migrations.AlterModelOptions(
            name='parent',
            options={'ordering': ['name']},
        ),
        migrations.AlterField(
            model_name='studentparent',
            name='relationship',
            field=models.CharField(
                choices=[
                    ('father', 'Father'),
                    ('mother', 'Mother'),
                    ('guardian', 'Guardian'),
                    ('other', 'Other'),
                    ('uncle', 'Uncle'),
                    ('aunt', 'Aunt'),
                    ('cousin', 'Cousin'),
                    ('sibling', 'Sibling'),
                    ('grandparent', 'Grandparent'),
                ],
                max_length=20,
            ),
        ),
    ]
