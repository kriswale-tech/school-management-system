import uuid
from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import F


def clear_stub_assessment_configs(apps, schema_editor):
    AssessmentConfig = apps.get_model('assessments', 'AssessmentConfig')
    AssessmentConfig.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0004_level_subject'),
        ('assessments', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(clear_stub_assessment_configs, migrations.RunPython.noop),
        migrations.AddField(
            model_name='assessmentconfig',
            name='continuous_assessment_weight',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('40.00'),
                help_text='Continuous assessment weight as a percentage of the total.',
                max_digits=5,
            ),
        ),
        migrations.AddField(
            model_name='assessmentconfig',
            name='exam_weight',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('60.00'),
                help_text='Exam weight as a percentage of the total.',
                max_digits=5,
            ),
        ),
        migrations.AddField(
            model_name='assessmentconfig',
            name='grade_type',
            field=models.CharField(
                blank=True,
                choices=[('letter', 'Letter grades (A–F)'), ('numerical', 'Numerical grades (1–9)')],
                help_text='Required when result type includes grades.',
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='assessmentconfig',
            name='result_type',
            field=models.CharField(
                choices=[
                    ('position', 'Position'),
                    ('grade', 'Grade'),
                    ('grade_and_position', 'Grade and Position'),
                ],
                default='grade_and_position',
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='assessmentconfig',
            name='level',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='assessment_config',
                to='academics.level',
            ),
        ),
        migrations.CreateModel(
            name='GradeBand',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('grade', models.CharField(help_text='Letter (A–F) or numerical (1–9) grade label.', max_length=10)),
                ('min_score', models.PositiveSmallIntegerField()),
                ('max_score', models.PositiveSmallIntegerField()),
                ('remark', models.CharField(max_length=100)),
                ('order', models.PositiveSmallIntegerField(default=1)),
                (
                    'assessment_config',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='grade_bands',
                        to='assessments.assessmentconfig',
                    ),
                ),
            ],
            options={
                'ordering': ['-min_score', 'order', 'grade'],
            },
        ),
        migrations.AddConstraint(
            model_name='assessmentconfig',
            constraint=models.CheckConstraint(
                condition=models.Q(('continuous_assessment_weight__gte', 0), ('exam_weight__gte', 0)),
                name='assessment_config_weights_non_negative',
            ),
        ),
        migrations.AddConstraint(
            model_name='assessmentconfig',
            constraint=models.CheckConstraint(
                condition=models.Q(('continuous_assessment_weight', 100 - F('exam_weight'))),
                name='assessment_config_weights_sum_100',
            ),
        ),
        migrations.AddConstraint(
            model_name='gradeband',
            constraint=models.UniqueConstraint(
                fields=('assessment_config', 'grade'),
                name='unique_grade_label_per_assessment_config',
            ),
        ),
        migrations.AddConstraint(
            model_name='gradeband',
            constraint=models.CheckConstraint(
                condition=models.Q(('min_score__lte', F('max_score'))),
                name='grade_band_min_lte_max',
            ),
        ),
        migrations.AddConstraint(
            model_name='gradeband',
            constraint=models.CheckConstraint(
                condition=models.Q(('max_score__lte', 100)),
                name='grade_band_max_score_lte_100',
            ),
        ),
    ]
