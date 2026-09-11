import uuid
from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assessments', '0003_alter_assessmentconfig_grade_type_and_more'),
        ('students', '0009_student_address_is_active'),
        ('teachers', '0002_teacher_assignments'),
    ]

    operations = [
        migrations.DeleteModel(name='AssessmentItemScore'),
        migrations.DeleteModel(name='AssessmentItem'),
        migrations.DeleteModel(name='SubjectScore'),
        migrations.CreateModel(
            name='AssessmentItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('max_marks', models.DecimalField(decimal_places=2, max_digits=7)),
                ('order', models.PositiveSmallIntegerField(default=1)),
                (
                    'teaching_assignment',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='assessment_items',
                        to='teachers.teachingassignment',
                    ),
                ),
            ],
            options={
                'ordering': ['order', 'created_at', 'name'],
                'constraints': [
                    models.UniqueConstraint(
                        fields=('teaching_assignment', 'name'),
                        name='unique_assessment_item_name_per_assignment',
                    ),
                    models.CheckConstraint(
                        condition=models.Q(('max_marks__gt', 0)),
                        name='assessment_item_max_marks_positive',
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name='AssessmentItemScore',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('mark', models.DecimalField(decimal_places=2, max_digits=7)),
                (
                    'assessment_item',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='scores',
                        to='assessments.assessmentitem',
                    ),
                ),
                (
                    'student',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='assessment_item_scores',
                        to='students.student',
                    ),
                ),
            ],
            options={
                'constraints': [
                    models.UniqueConstraint(
                        fields=('assessment_item', 'student'),
                        name='unique_score_per_student_assessment_item',
                    ),
                    models.CheckConstraint(
                        condition=models.Q(('mark__gte', 0)),
                        name='assessment_item_score_mark_non_negative',
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name='SubjectScore',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'exam_mark',
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text='Exam mark out of 100. Null until the exam is recorded.',
                        max_digits=5,
                        null=True,
                    ),
                ),
                (
                    'student',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='subject_scores',
                        to='students.student',
                    ),
                ),
                (
                    'teaching_assignment',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='subject_scores',
                        to='teachers.teachingassignment',
                    ),
                ),
            ],
            options={
                'constraints': [
                    models.UniqueConstraint(
                        fields=('teaching_assignment', 'student'),
                        name='unique_subject_score_per_student_assignment',
                    ),
                    models.CheckConstraint(
                        condition=models.Q(('exam_mark__isnull', True))
                        | (
                            models.Q(('exam_mark__gte', 0))
                            & models.Q(('exam_mark__lte', 100))
                        ),
                        name='subject_score_exam_mark_0_to_100',
                    ),
                ],
            },
        ),
    ]
