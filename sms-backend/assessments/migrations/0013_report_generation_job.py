import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0004_level_subject'),
        ('assessments', '0012_assessmentconfig_pass_mark'),
        ('schools', '0006_guardians_alert_enabled'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='generation_id',
            field=models.UUIDField(
                blank=True,
                db_index=True,
                help_text='Changes on each successful PDF write; used for notify idempotency.',
                null=True,
            ),
        ),
        migrations.CreateModel(
            name='ReportGenerateJob',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('pending', 'Pending'),
                            ('running', 'Running'),
                            ('completed', 'Completed'),
                            ('failed', 'Failed'),
                        ],
                        default='pending',
                        max_length=20,
                    ),
                ),
                (
                    'force',
                    models.BooleanField(
                        default=False,
                        help_text='When true, regenerate even if an R2 file already exists.',
                    ),
                ),
                ('student_ids', models.JSONField(blank=True, default=list)),
                ('total', models.PositiveIntegerField(default=0)),
                ('generated', models.PositiveIntegerField(default=0)),
                ('skipped', models.PositiveIntegerField(default=0)),
                ('failed', models.PositiveIntegerField(default=0)),
                ('error_message', models.CharField(blank=True, default='', max_length=500)),
                (
                    'failures',
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text='[{student_id, full_name, reason}, ...] truncated list.',
                    ),
                ),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                (
                    'created_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='report_generate_jobs',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'school',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='report_generate_jobs',
                        to='schools.school',
                    ),
                ),
                (
                    'stream',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='report_generate_jobs',
                        to='academics.classstream',
                    ),
                ),
                (
                    'term',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='report_generate_jobs',
                        to='schools.term',
                    ),
                ),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='reportgeneratejob',
            index=models.Index(
                fields=['school', 'stream', 'term', '-created_at'],
                name='assessments_school__7a2c1d_idx',
            ),
        ),
    ]
