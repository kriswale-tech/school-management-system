import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0004_level_subject'),
        ('schools', '0001_initial'),
        ('teachers', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='classteacher',
            name='class_level',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='class_teachers',
                to='academics.classlevel',
            ),
        ),
        migrations.AddField(
            model_name='classteacher',
            name='stream',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='class_teachers',
                to='academics.classstream',
            ),
        ),
        migrations.AddField(
            model_name='classteacher',
            name='teacher',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='class_teacher_assignments',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='classteacher',
            name='term',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='class_teachers',
                to='schools.term',
            ),
        ),
        migrations.AddField(
            model_name='teachingassignment',
            name='class_subject',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='teaching_assignments',
                to='academics.classsubject',
            ),
        ),
        migrations.AddField(
            model_name='teachingassignment',
            name='stream',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='teaching_assignments',
                to='academics.classstream',
            ),
        ),
        migrations.AddField(
            model_name='teachingassignment',
            name='subject_group',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='teaching_assignments',
                to='academics.subjectgroup',
            ),
        ),
        migrations.AddField(
            model_name='teachingassignment',
            name='teacher',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='teaching_assignments',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='teachingassignment',
            name='term',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='teaching_assignments',
                to='schools.term',
            ),
        ),
        migrations.AddConstraint(
            model_name='classteacher',
            constraint=models.UniqueConstraint(
                condition=models.Q(stream__isnull=True),
                fields=('class_level', 'term'),
                name='unique_class_teacher_per_class_term',
            ),
        ),
        migrations.AddConstraint(
            model_name='classteacher',
            constraint=models.UniqueConstraint(
                condition=models.Q(stream__isnull=False),
                fields=('class_level', 'stream', 'term'),
                name='unique_class_teacher_per_stream_term',
            ),
        ),
        migrations.AddConstraint(
            model_name='teachingassignment',
            constraint=models.UniqueConstraint(
                condition=models.Q(stream__isnull=True, subject_group__isnull=True),
                fields=('class_subject', 'term'),
                name='unique_teaching_assignment_per_class_subject_term',
            ),
        ),
        migrations.AddConstraint(
            model_name='teachingassignment',
            constraint=models.UniqueConstraint(
                condition=models.Q(stream__isnull=False, subject_group__isnull=True),
                fields=('class_subject', 'stream', 'term'),
                name='unique_teaching_assignment_per_stream_term',
            ),
        ),
        migrations.AddConstraint(
            model_name='teachingassignment',
            constraint=models.UniqueConstraint(
                condition=models.Q(subject_group__isnull=False),
                fields=('class_subject', 'subject_group', 'term'),
                name='unique_teaching_assignment_per_subject_group_term',
            ),
        ),
    ]
