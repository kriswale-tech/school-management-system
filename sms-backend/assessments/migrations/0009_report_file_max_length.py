from django.db import migrations, models

import assessments.storage


class Migration(migrations.Migration):

    dependencies = [
        ('assessments', '0008_report_pdf_storage'),
    ]

    operations = [
        migrations.AlterField(
            model_name='report',
            name='file',
            field=models.FileField(
                blank=True,
                max_length=500,
                storage=assessments.storage.report_storage,
                upload_to=assessments.storage.report_upload_to,
            ),
        ),
    ]
