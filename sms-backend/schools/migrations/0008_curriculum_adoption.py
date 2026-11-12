from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0005_curriculum_versions'),
        ('schools', '0007_school_lifecycle'),
    ]

    operations = [
        migrations.AddField(
            model_name='school',
            name='accepted_curriculum',
            field=models.ForeignKey(
                blank=True,
                help_text='Version the school has accepted. It is applied when the next term starts.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='schools_accepting',
                to='academics.curriculum',
            ),
        ),
        migrations.AddField(
            model_name='schoolsettings',
            name='curriculum_alert_enabled',
            field=models.BooleanField(
                default=True,
                help_text='Show the curriculum update on the bell and the admin dashboard.',
            ),
        ),
    ]
