from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0005_auto_debt_reminders'),
    ]

    operations = [
        migrations.AddField(
            model_name='schoolsettings',
            name='guardians_alert_enabled',
            field=models.BooleanField(
                default=True,
                help_text=(
                    'Alert admins and staff when enrolled students have no linked guardian.'
                ),
            ),
        ),
    ]
