from datetime import timedelta

from django.db import migrations, models
from django.utils import timezone


def set_expires_at_from_created_at(apps, schema_editor):
    PhoneOtp = apps.get_model('accounts', 'PhoneOtp')
    for phone_otp in PhoneOtp.objects.all():
        phone_otp.expires_at = phone_otp.created_at + timedelta(minutes=5)
        phone_otp.save(update_fields=['expires_at'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_role_as_user_choice_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='phoneotp',
            name='expires_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.RunPython(set_expires_at_from_created_at, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='phoneotp',
            name='expires_at',
            field=models.DateTimeField(),
        ),
    ]
