from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0006_messages_module'),
    ]

    operations = [
        migrations.AlterField(
            model_name='platformoutbounddelivery',
            name='provider',
            field=models.CharField(
                choices=[
                    ('arkesel', 'Arkesel'),
                    ('ses', 'Amazon SES'),
                    ('resend', 'Resend (legacy)'),
                    ('django', 'Django mail backend'),
                    ('other', 'Other'),
                ],
                default='other',
                max_length=20,
            ),
        ),
    ]
