from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0004_guardian_communications'),
    ]

    operations = [
        migrations.AddField(
            model_name='schoolsettings',
            name='guardian_debt_reminder_auto_enabled',
            field=models.BooleanField(
                default=False,
                help_text='Automatically remind guardians of outstanding balances on a schedule.',
            ),
        ),
        migrations.AddField(
            model_name='schoolsettings',
            name='guardian_debt_reminder_frequency',
            field=models.CharField(
                choices=[
                    ('end_of_month', 'End of each month'),
                    ('weekly', 'Weekly (Mondays)'),
                    ('biweekly', 'Every 2 weeks (Mondays)'),
                ],
                default='end_of_month',
                help_text='How often automatic debt reminders are sent (default: end of each month).',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='schoolsettings',
            name='guardian_debt_reminder_enabled',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'Allow debt reminders to guardians '
                    '(manual Fees desk and optional automation).'
                ),
            ),
        ),
    ]
