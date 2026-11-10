from django.db import migrations, models


def attach_existing_skus_to_all_plans(apps, schema_editor):
    """Preserve pre-gating behaviour: existing SKUs remain available on every plan."""
    CommunicationAddonSku = apps.get_model('communications', 'CommunicationAddonSku')
    Plan = apps.get_model('billing', 'Plan')
    plan_ids = list(Plan.objects.values_list('pk', flat=True))
    if not plan_ids:
        return
    Through = CommunicationAddonSku.available_plans.through
    rows = []
    for sku_id in CommunicationAddonSku.objects.values_list('pk', flat=True):
        for plan_id in plan_ids:
            rows.append(
                Through(
                    communicationaddonsku_id=sku_id,
                    plan_id=plan_id,
                ),
            )
    if rows:
        Through.objects.bulk_create(rows, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0006_topup_discount'),
        ('communications', '0003_provider_ses'),
    ]

    operations = [
        migrations.AlterField(
            model_name='communicationaddonsku',
            name='is_active',
            field=models.BooleanField(
                default=False,
                help_text='Inactive until explicitly activated. Schools only see active SKUs.',
            ),
        ),
        migrations.AddField(
            model_name='communicationaddonsku',
            name='available_plans',
            field=models.ManyToManyField(
                blank=True,
                help_text='Plans that may opt into this SKU.',
                related_name='communication_addon_skus',
                to='billing.plan',
            ),
        ),
        migrations.RunPython(attach_existing_skus_to_all_plans, migrations.RunPython.noop),
    ]
