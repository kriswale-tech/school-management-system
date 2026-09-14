import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('assessments', '0005_publish_and_student_result'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentresult',
            name='head_teacher_remarks',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='studentresult',
            name='released_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='studentresult',
            name='released_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='released_student_results',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='studentresult',
            name='status',
            field=models.CharField(
                choices=[
                    ('awaiting_approval', 'Awaiting approval'),
                    ('approved', 'Approved'),
                    ('released', 'Released'),
                ],
                default='awaiting_approval',
                max_length=32,
            ),
        ),
    ]
