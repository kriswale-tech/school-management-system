from django.db import migrations


def forwards_map_legacy_statuses(apps, schema_editor):
    GuardianDelivery = apps.get_model('notifications', 'GuardianDelivery')
    GuardianDelivery.objects.filter(status='sent').update(status='submitted')
    for row in GuardianDelivery.objects.filter(body_text='').exclude(body_preview='').iterator():
        row.body_text = row.body_preview
        row.save(update_fields=['body_text'])


def backwards_map_legacy_statuses(apps, schema_editor):
    GuardianDelivery = apps.get_model('notifications', 'GuardianDelivery')
    GuardianDelivery.objects.filter(status='submitted').update(status='sent')


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0003_sms_delivery_lifecycle'),
    ]

    operations = [
        migrations.RunPython(forwards_map_legacy_statuses, backwards_map_legacy_statuses),
    ]
