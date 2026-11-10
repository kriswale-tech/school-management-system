from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0005_phase6_dunning_interval'),
    ]

    operations = [
        migrations.AddField(
            model_name='topuppackage',
            name='discount_percent',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                help_text=(
                    'Direct package discount applied to list price '
                    '(credits × Messages sell price).'
                ),
                max_digits=5,
            ),
        ),
    ]
