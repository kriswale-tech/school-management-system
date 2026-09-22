import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import assessments.storage


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0004_level_subject'),
        ('assessments', '0007_studentresult_conduct_attitude_interest'),
        ('schools', '0001_initial'),
        ('students', '0009_student_address_is_active'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='file',
            field=models.FileField(
                blank=True,
                storage=assessments.storage.report_storage,
                upload_to=assessments.storage.report_upload_to,
            ),
        ),
        migrations.AddField(
            model_name='report',
            name='generated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='report',
            name='generated_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='generated_assessment_reports',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='report',
            name='school',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='assessment_reports',
                to='schools.school',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='report',
            name='stream',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='assessment_reports',
                to='academics.classstream',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='report',
            name='student',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='assessment_reports',
                to='students.student',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='report',
            name='term',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='assessment_reports',
                to='schools.term',
            ),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name='report',
            constraint=models.UniqueConstraint(
                fields=('school', 'student', 'stream', 'term'),
                name='unique_report_student_stream_term',
            ),
        ),
    ]
