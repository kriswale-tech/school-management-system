import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0010_student_is_graduated'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='leave_notes',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='student',
            name='leave_reason',
            field=models.CharField(
                blank=True,
                choices=[
                    ('dropout', 'Dropped out'),
                    ('transfer', 'Transferred'),
                    ('other', 'Other'),
                ],
                default='',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='student',
            name='left_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When the student was marked as having left the school.',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='student',
            name='left_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='students_marked_left',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
