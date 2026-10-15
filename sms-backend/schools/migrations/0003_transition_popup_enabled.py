from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0002_school_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='schoolsettings',
            name='transition_popup_enabled',
            field=models.BooleanField(
                default=True,
                help_text='Show a popup on the dashboard while opening the next term still needs action.',
            ),
        ),
    ]
