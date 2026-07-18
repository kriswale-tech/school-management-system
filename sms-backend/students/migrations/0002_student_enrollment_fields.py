import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0002_initial'),
        ('schools', '0001_initial'),
        ('students', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='first_name',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='student',
            name='last_name',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='student',
            name='school',
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='students',
                to='schools.school',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='classenrollment',
            name='class_level',
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='enrollments',
                to='academics.classlevel',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='classenrollment',
            name='is_new_student',
            field=models.BooleanField(
                default=False,
                help_text="True when this is the student's first term at the school.",
            ),
        ),
        migrations.AddField(
            model_name='classenrollment',
            name='student',
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='enrollments',
                to='students.student',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='classenrollment',
            name='term',
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='enrollments',
                to='schools.term',
            ),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name='classenrollment',
            constraint=models.UniqueConstraint(
                fields=('student', 'term'),
                name='unique_student_enrollment_per_term',
            ),
        ),
    ]
