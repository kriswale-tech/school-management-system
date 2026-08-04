from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0008_unique_student_id_per_school'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='address',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Place of residence.',
            ),
        ),
        migrations.AddField(
            model_name='student',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]
