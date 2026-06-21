from django.db import migrations, models
from django.utils import timezone


def set_sent_at_from_updated_at(apps, schema_editor):
    PhoneOtp = apps.get_model('accounts', 'PhoneOtp')
    for phone_otp in PhoneOtp.objects.all():
        phone_otp.sent_at = phone_otp.updated_at or phone_otp.created_at or timezone.now()
        phone_otp.save(update_fields=['sent_at'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_phoneotp_expires_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='phoneotp',
            name='sent_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.RunPython(set_sent_at_from_updated_at, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='phoneotp',
            name='sent_at',
            field=models.DateTimeField(),
        ),
    ]
