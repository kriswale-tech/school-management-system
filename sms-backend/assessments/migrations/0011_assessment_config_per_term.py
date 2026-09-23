import uuid
from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


def backfill_term_assessment_configs(apps, schema_editor):
    AssessmentConfig = apps.get_model('assessments', 'AssessmentConfig')
    GradeBand = apps.get_model('assessments', 'GradeBand')
    Term = apps.get_model('schools', 'Term')

    configs = list(
        AssessmentConfig.objects.select_related('level').prefetch_related('grade_bands')
    )
    for config in configs:
        terms = list(
            Term.objects.filter(school_id=config.level.school_id).order_by('start_date', 'id')
        )
        if not terms:
            config.delete()
            continue
        keep = next((term for term in terms if term.is_active), terms[-1])
        if config.term_id != keep.id:
            config.term_id = keep.id
            config.save(update_fields=['term_id'])

        band_rows = list(config.grade_bands.all())
        now = timezone.now()
        for term in terms:
            if term.id == keep.id:
                continue
            if AssessmentConfig.objects.filter(level_id=config.level_id, term_id=term.id).exists():
                continue
            clone = AssessmentConfig.objects.create(
                level_id=config.level_id,
                term_id=term.id,
                continuous_assessment_weight=config.continuous_assessment_weight,
                exam_weight=config.exam_weight,
                result_type=config.result_type,
                grade_type=config.grade_type,
            )
            GradeBand.objects.bulk_create([
                GradeBand(
                    id=uuid.uuid4(),
                    created_at=now,
                    updated_at=now,
                    assessment_config=clone,
                    grade=band.grade,
                    min_score=band.min_score,
                    max_score=band.max_score,
                    remark=band.remark,
                    order=band.order,
                )
                for band in band_rows
            ])


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('academics', '0004_level_subject'),
        ('assessments', '0010_correction_request_workflow'),
        ('schools', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='assessmentconfig',
            name='term',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='assessment_configs',
                to='schools.term',
            ),
        ),
        migrations.AlterField(
            model_name='assessmentconfig',
            name='level',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='assessment_configs',
                to='academics.level',
            ),
        ),
        migrations.RunPython(backfill_term_assessment_configs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='assessmentconfig',
            name='term',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='assessment_configs',
                to='schools.term',
            ),
        ),
        migrations.AddConstraint(
            model_name='assessmentconfig',
            constraint=models.UniqueConstraint(
                fields=('level', 'term'),
                name='unique_assessment_config_per_level_term',
            ),
        ),
    ]
