# Generated manually for Amazon SES provider cutover.

from django.db import migrations, models


PROVIDER_CHOICES = [
    ('arkesel', 'Arkesel'),
    ('ses', 'Amazon SES'),
    ('resend', 'Resend (legacy)'),
]


class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0002_messages_module'),
    ]

    operations = [
        migrations.AlterField(
            model_name='provideraccount',
            name='provider',
            field=models.CharField(choices=PROVIDER_CHOICES, max_length=20),
        ),
        migrations.AlterField(
            model_name='providerexpense',
            name='provider',
            field=models.CharField(
                choices=PROVIDER_CHOICES,
                default='ses',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='providerpurchase',
            name='provider',
            field=models.CharField(
                choices=PROVIDER_CHOICES,
                default='arkesel',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='providerreconciliationitem',
            name='provider',
            field=models.CharField(choices=PROVIDER_CHOICES, max_length=20),
        ),
        migrations.AlterField(
            model_name='providerreconciliationrun',
            name='provider',
            field=models.CharField(choices=PROVIDER_CHOICES, max_length=20),
        ),
    ]
