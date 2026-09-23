import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0004_level_subject'),
        ('assessments', '0009_report_file_max_length'),
        ('schools', '0001_initial'),
        ('students', '0009_student_address_is_active'),
        ('teachers', '0002_teacher_assignments'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='studentresult',
            name='status',
            field=models.CharField(
                choices=[
                    ('awaiting_approval', 'Awaiting approval'),
                    ('approved', 'Approved'),
                    ('released', 'Released'),
                    ('needs_correction', 'Needs correction'),
                ],
                default='awaiting_approval',
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name='correctionrequest',
            name='applied_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='correctionrequest',
            name='kind',
            field=models.CharField(
                choices=[
                    ('reject', 'Reject'),
                    ('reopen', 'Reopen'),
                    ('reopen_request', 'Reopen request'),
                ],
                default='reject',
                max_length=32,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='correctionrequest',
            name='previous_result_status',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
        migrations.AddField(
            model_name='correctionrequest',
            name='raised_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='correctionrequest',
            name='raised_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='raised_correction_requests',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='correctionrequest',
            name='reason',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='correctionrequest',
            name='resolved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='correctionrequest',
            name='reviewed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='correctionrequest',
            name='reviewed_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='reviewed_correction_requests',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='correctionrequest',
            name='school',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='correction_requests',
                to='schools.school',
            ),
        ),
        migrations.AddField(
            model_name='correctionrequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('open', 'Open'),
                    ('declined', 'Declined'),
                    ('applied', 'Applied'),
                    ('resolved', 'Resolved'),
                ],
                default='open',
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name='correctionrequest',
            name='stream',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='correction_requests',
                to='academics.classstream',
            ),
        ),
        migrations.AddField(
            model_name='correctionrequest',
            name='student',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='correction_requests',
                to='students.student',
            ),
        ),
        migrations.AddField(
            model_name='correctionrequest',
            name='term',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='correction_requests',
                to='schools.term',
            ),
        ),
        migrations.AlterModelOptions(
            name='correctionrequest',
            options={'ordering': ['-raised_at']},
        ),
        migrations.RunPython(
            code=migrations.RunPython.noop,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunSQL(
            sql="DELETE FROM assessments_correctionrequest;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AlterField(
            model_name='correctionrequest',
            name='raised_at',
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name='correctionrequest',
            name='school',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='correction_requests',
                to='schools.school',
            ),
        ),
        migrations.AlterField(
            model_name='correctionrequest',
            name='stream',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='correction_requests',
                to='academics.classstream',
            ),
        ),
        migrations.AlterField(
            model_name='correctionrequest',
            name='student',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='correction_requests',
                to='students.student',
            ),
        ),
        migrations.AlterField(
            model_name='correctionrequest',
            name='term',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='correction_requests',
                to='schools.term',
            ),
        ),
        migrations.CreateModel(
            name='CorrectionRequestSubject',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('subject_label', models.CharField(blank=True, default='', max_length=255)),
                ('correction_request', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='subjects',
                    to='assessments.correctionrequest',
                )),
                ('teaching_assignment', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='correction_request_subjects',
                    to='teachers.teachingassignment',
                )),
            ],
            options={
                'constraints': [
                    models.UniqueConstraint(
                        fields=('correction_request', 'teaching_assignment'),
                        name='unique_correction_request_teaching_assignment',
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name='CorrectionRequestEvent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('event_type', models.CharField(max_length=64)),
                ('detail', models.JSONField(blank=True, default=dict)),
                ('occurred_at', models.DateTimeField()),
                ('actor', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='correction_request_events',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('correction_request', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='events',
                    to='assessments.correctionrequest',
                )),
            ],
            options={
                'ordering': ['occurred_at', 'created_at'],
            },
        ),
    ]
