import uuid

from django.db import migrations, models


def fill_lineage(apps, schema_editor):
    from academics.curriculum_guard import allow_curriculum_writes

    with allow_curriculum_writes():
        for model_name in ('CurriculumLevel', 'CurriculumClassLevel', 'CurriculumSubject'):
            model = apps.get_model('academics', model_name)
            for row in model.objects.all().iterator():
                row.lineage_id = row.id
                row.save(update_fields=['lineage_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0004_level_subject'),
    ]

    operations = [
        migrations.AddField(
            model_name='curriculum',
            name='published_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='curriculum',
            name='status',
            field=models.CharField(
                choices=[('draft', 'Draft'), ('published', 'Published')],
                default='published',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='curriculumlevel',
            name='lineage_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='curriculumclasslevel',
            name='lineage_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='curriculumsubject',
            name='lineage_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.RunPython(fill_lineage, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='curriculumlevel',
            name='lineage_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
        migrations.AlterField(
            model_name='curriculumclasslevel',
            name='lineage_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
        migrations.AlterField(
            model_name='curriculumsubject',
            name='lineage_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
    ]
