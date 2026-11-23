import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fees', '0009_fee_schedule_document'),
    ]

    operations = [
        migrations.AlterField(
            model_name='feescheduledocument',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
    ]
