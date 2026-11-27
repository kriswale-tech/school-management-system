from django.db import migrations, models
import shared.uploads


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0008_curriculum_adoption'),
    ]

    operations = [
        migrations.AlterField(
            model_name='school',
            name='logo',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to=shared.uploads.school_logo_upload_to,
            ),
        ),
    ]
