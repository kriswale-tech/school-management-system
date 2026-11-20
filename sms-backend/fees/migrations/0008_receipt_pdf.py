from django.db import migrations, models

import fees.storage


class Migration(migrations.Migration):

    dependencies = [
        ('fees', '0007_historical_finance'),
    ]

    operations = [
        migrations.AddField(
            model_name='receipt',
            name='file',
            field=models.FileField(
                blank=True,
                max_length=500,
                storage=fees.storage.receipt_storage,
                upload_to=fees.storage.receipt_upload_to,
            ),
        ),
    ]
