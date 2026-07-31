from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0005_parent_name_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='student_id',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
    ]
