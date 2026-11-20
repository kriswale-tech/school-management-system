import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0006_phase2_student_enrollment'),
        ('migration', '0002_phase2_student_enrollment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='migrationjob',
            name='template',
            field=models.CharField(blank=True, default='', max_length=40),
        ),
        migrations.CreateModel(
            name='ClassValueResolution',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('source_value', models.CharField(max_length=255)),
                ('use_snapshot', models.BooleanField(default=False)),
                ('confirmed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='migration_class_resolutions', to=settings.AUTH_USER_MODEL)),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='class_resolutions', to='migration.migrationjob')),
                ('stream', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='migration_class_resolutions', to='academics.classstream')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddConstraint(
            model_name='classvalueresolution',
            constraint=models.UniqueConstraint(fields=('job', 'source_value'), name='unique_migration_class_source_value'),
        ),
    ]
