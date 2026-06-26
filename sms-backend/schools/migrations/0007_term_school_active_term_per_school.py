import uuid

import django.db.models.deletion
from django.db import migrations, models


def populate_term_school(apps, schema_editor):
    Term = apps.get_model('schools', 'Term')
    for term in Term.objects.select_related('academic_year').all():
        term.school_id = term.academic_year.school_id
        term.save(update_fields=['school_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0006_academicyear_term'),
    ]

    operations = [
        migrations.AddField(
            model_name='term',
            name='school',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='terms',
                to='schools.school',
            ),
        ),
        migrations.RunPython(populate_term_school, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='term',
            name='school',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='terms',
                to='schools.school',
            ),
        ),
        migrations.RemoveConstraint(
            model_name='term',
            name='unique_active_term_per_academic_year',
        ),
        migrations.AddConstraint(
            model_name='term',
            constraint=models.UniqueConstraint(
                condition=models.Q(('is_active', True)),
                fields=('school',),
                name='unique_active_term_per_school',
            ),
        ),
    ]
