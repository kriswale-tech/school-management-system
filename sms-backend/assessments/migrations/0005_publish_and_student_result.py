import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0004_level_subject'),
        ('assessments', '0004_assessment_items_and_scores'),
        ('schools', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('students', '0009_student_address_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='subjectscore',
            name='is_published',
            field=models.BooleanField(
                default=False,
                help_text='True when the subject teacher has released this result to the class teacher.',
            ),
        ),
        migrations.AddField(
            model_name='subjectscore',
            name='published_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.DeleteModel(name='StudentResult'),
        migrations.CreateModel(
            name='StudentResult',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('awaiting_approval', 'Awaiting approval'),
                            ('approved', 'Approved'),
                        ],
                        default='awaiting_approval',
                        max_length=32,
                    ),
                ),
                ('remarks', models.TextField(blank=True, default='')),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                (
                    'approved_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='approved_student_results',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'class_level',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='student_assessment_results',
                        to='academics.classlevel',
                    ),
                ),
                (
                    'stream',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='student_assessment_results',
                        to='academics.classstream',
                    ),
                ),
                (
                    'student',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='assessment_results',
                        to='students.student',
                    ),
                ),
                (
                    'term',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='student_assessment_results',
                        to='schools.term',
                    ),
                ),
            ],
            options={
                'constraints': [
                    models.UniqueConstraint(
                        condition=models.Q(('stream__isnull', True)),
                        fields=('student', 'term', 'class_level'),
                        name='unique_student_result_whole_class_term',
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(('stream__isnull', False)),
                        fields=('student', 'term', 'class_level', 'stream'),
                        name='unique_student_result_stream_term',
                    ),
                ],
            },
        ),
    ]
