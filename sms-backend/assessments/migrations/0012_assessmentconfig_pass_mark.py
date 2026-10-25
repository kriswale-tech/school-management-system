from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assessments', '0011_assessment_config_per_term'),
    ]

    operations = [
        migrations.AddField(
            model_name='assessmentconfig',
            name='pass_mark',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('40.00'),
                help_text=(
                    'Minimum overall / subject total (out of 100) treated as a pass '
                    'in reports and related views.'
                ),
                max_digits=5,
            ),
        ),
        migrations.AddConstraint(
            model_name='assessmentconfig',
            constraint=models.CheckConstraint(
                condition=models.Q(('pass_mark__gte', 0), ('pass_mark__lte', 100)),
                name='assessment_config_pass_mark_0_to_100',
            ),
        ),
    ]
