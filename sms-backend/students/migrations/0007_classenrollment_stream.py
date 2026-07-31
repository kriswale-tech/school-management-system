import django.db.models.deletion
from django.db import migrations, models


def backfill_enrollment_streams(apps, schema_editor):
    ClassEnrollment = apps.get_model('students', 'ClassEnrollment')
    ClassStream = apps.get_model('academics', 'ClassStream')

    for enrollment in ClassEnrollment.objects.all().iterator():
        stream = ClassStream.objects.filter(
            class_level_id=enrollment.class_level_id,
            is_default=True,
        ).first()
        if stream is None:
            stream = ClassStream.objects.create(
                class_level_id=enrollment.class_level_id,
                name='',
                is_default=True,
                is_active=True,
            )
        enrollment.stream_id = stream.id
        enrollment.save(update_fields=['stream_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0004_level_subject'),
        ('students', '0006_student_student_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='classenrollment',
            name='stream',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='enrollments',
                to='academics.classstream',
            ),
        ),
        migrations.RunPython(backfill_enrollment_streams, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='classenrollment',
            name='stream',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='enrollments',
                to='academics.classstream',
            ),
        ),
    ]
