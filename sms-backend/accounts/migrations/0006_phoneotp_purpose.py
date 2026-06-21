from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_phoneotp_sent_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='phoneotp',
            name='purpose',
            field=models.CharField(
                choices=[('signup', 'Signup'), ('login', 'Login')],
                default='signup',
                max_length=10,
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='phoneotp',
            name='phone_number',
            field=models.CharField(max_length=15),
        ),
        migrations.AlterUniqueTogether(
            name='phoneotp',
            unique_together={('phone_number', 'purpose')},
        ),
    ]
