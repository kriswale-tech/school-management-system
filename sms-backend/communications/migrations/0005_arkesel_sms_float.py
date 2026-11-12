from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0004_addon_plan_gating'),
    ]

    operations = [
        migrations.AddField(
            model_name='provideraccount',
            name='sms_float_reserved',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Units promised to an in-flight Arkesel request.',
            ),
        ),
        migrations.AddField(
            model_name='provideraccount',
            name='sms_float_synced_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When sms_float_units was last set from an Arkesel balance.',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='provideraccount',
            name='sms_float_units',
            field=models.IntegerField(
                blank=True,
                help_text='Units still safe to promise. Null until a balance is recorded.',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='provideraccount',
            name='sms_hold_alerted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='provideraccount',
            name='sms_low_balance_alerted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
