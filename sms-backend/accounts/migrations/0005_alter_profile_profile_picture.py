from django.db import migrations, models
import shared.uploads


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_schoolmembership_staff_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='profile_picture',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to=shared.uploads.profile_picture_upload_to,
            ),
        ),
    ]
