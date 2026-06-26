import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0005_alter_school_logo_alter_schoolsetup_current_step'),
    ]

    operations = [
        migrations.AddField(
            model_name='academicyear',
            name='academic_year',
            field=models.CharField(default='2000/2001', max_length=9),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='academicyear',
            name='end_date',
            field=models.DateField(default='2001-07-31'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='academicyear',
            name='is_active',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='academicyear',
            name='school',
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='academic_years',
                to='schools.school',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='academicyear',
            name='start_date',
            field=models.DateField(default='2000-09-01'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='term',
            name='academic_year',
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='terms',
                to='schools.academicyear',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='term',
            name='end_date',
            field=models.DateField(default='2000-12-15'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='term',
            name='is_active',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='term',
            name='start_date',
            field=models.DateField(default='2000-09-01'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='term',
            name='term',
            field=models.CharField(
                choices=[
                    ('first_term', 'First Term'),
                    ('second_term', 'Second Term'),
                    ('third_term', 'Third Term'),
                ],
                default='first_term',
                max_length=15,
            ),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name='academicyear',
            constraint=models.UniqueConstraint(
                condition=models.Q(('is_active', True)),
                fields=('school',),
                name='unique_active_academic_year_per_school',
            ),
        ),
        migrations.AddConstraint(
            model_name='academicyear',
            constraint=models.UniqueConstraint(
                fields=('school', 'academic_year'),
                name='unique_academic_year_label_per_school',
            ),
        ),
        migrations.AddConstraint(
            model_name='term',
            constraint=models.UniqueConstraint(
                condition=models.Q(('is_active', True)),
                fields=('academic_year',),
                name='unique_active_term_per_academic_year',
            ),
        ),
        migrations.AddConstraint(
            model_name='term',
            constraint=models.UniqueConstraint(
                fields=('academic_year', 'term'),
                name='unique_term_per_academic_year',
            ),
        ),
    ]
