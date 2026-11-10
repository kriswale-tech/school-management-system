from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0006_topup_discount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='plan',
            name='is_active',
            field=models.BooleanField(
                default=False,
                help_text='Inactive until explicitly activated. Schools only see active plans.',
            ),
        ),
        migrations.AlterField(
            model_name='topuppackage',
            name='is_active',
            field=models.BooleanField(
                default=False,
                help_text='Inactive until explicitly activated. Schools only see active packages.',
            ),
        ),
    ]
