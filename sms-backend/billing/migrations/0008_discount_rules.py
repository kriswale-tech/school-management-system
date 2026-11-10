from decimal import Decimal

from django.db import migrations, models


def snapshot_existing_discounts(apps, schema_editor):
    PromotionCampaign = apps.get_model('billing', 'PromotionCampaign')
    PromotionRedemption = apps.get_model('billing', 'PromotionRedemption')
    for campaign in PromotionCampaign.objects.all():
        campaign.schedule = 'introductory'
        campaign.audience = 'new' if campaign.first_subscription_only else 'all'
        campaign.billing_interval = ''
        campaign.save(update_fields=['schedule', 'audience', 'billing_interval'])
    for redemption in PromotionRedemption.objects.select_related('campaign'):
        campaign = redemption.campaign
        redemption.discount_percent = campaign.discount_percent
        redemption.applies_to = campaign.applies_to
        redemption.schedule = campaign.schedule
        redemption.billing_interval = ''
        redemption.save(
            update_fields=[
                'discount_percent',
                'applies_to',
                'schedule',
                'billing_interval',
            ],
        )


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0007_catalog_inactive_default'),
        ('schools', '0007_school_lifecycle'),
    ]

    operations = [
        migrations.AddField(
            model_name='promotioncampaign',
            name='schedule',
            field=models.CharField(
                choices=[
                    ('introductory', 'First months of the school'),
                    ('recurring', 'Every invoice'),
                    ('date_range', 'Date range'),
                ],
                default='introductory',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='promotioncampaign',
            name='audience',
            field=models.CharField(
                choices=[
                    ('all', 'All schools'),
                    ('new', 'New schools'),
                    ('selected', 'Selected schools'),
                ],
                default='new',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='promotioncampaign',
            name='billing_interval',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Blank applies on monthly and annual invoices. Otherwise the school must be on this interval.',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='promotioncampaign',
            name='schools',
            field=models.ManyToManyField(
                blank=True,
                related_name='promotion_campaigns',
                to='schools.school',
            ),
        ),
        migrations.AlterField(
            model_name='promotioncampaign',
            name='first_subscription_only',
            field=models.BooleanField(
                default=True,
                help_text="Kept in step with audience=new. Only a school's first subscription can redeem this.",
            ),
        ),
        migrations.AlterField(
            model_name='promotioncampaign',
            name='duration_months',
            field=models.PositiveSmallIntegerField(
                default=12,
                help_text='Introductory discounts cover this many months from the school subscription start.',
            ),
        ),
        migrations.AlterField(
            model_name='promotioncampaign',
            name='starts_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Date-range discounts include a billing month that starts on or after this moment.',
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='promotioncampaign',
            name='ends_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Date-range discounts stop at this moment. A month that starts here is full price.',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='promotionredemption',
            name='discount_percent',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                max_digits=5,
            ),
        ),
        migrations.AddField(
            model_name='promotionredemption',
            name='applies_to',
            field=models.CharField(
                choices=[
                    ('application', 'Application only'),
                    ('communication', 'Communication add-ons'),
                    ('all', 'Application and communication'),
                ],
                default='application',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='promotionredemption',
            name='schedule',
            field=models.CharField(
                choices=[
                    ('introductory', 'First months of the school'),
                    ('recurring', 'Every invoice'),
                    ('date_range', 'Date range'),
                ],
                default='introductory',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='promotionredemption',
            name='billing_interval',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='promotionredemption',
            name='revoked_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='promotionredemption',
            name='ends_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(snapshot_existing_discounts, migrations.RunPython.noop),
    ]
