from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assessments', '0006_studentresult_release'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentresult',
            name='conduct',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='studentresult',
            name='attitude',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='studentresult',
            name='interest',
            field=models.TextField(blank=True, default=''),
        ),
    ]
