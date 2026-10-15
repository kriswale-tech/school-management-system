from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0009_student_address_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='is_graduated',
            field=models.BooleanField(
                default=False,
                help_text='Finished the last class the school offers. Not enrolled in later years.',
            ),
        ),
    ]
