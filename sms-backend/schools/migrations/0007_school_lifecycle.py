from django.db import migrations, models
from django.utils import timezone


def mark_existing_schools_active(apps, schema_editor):
    School = apps.get_model('schools', 'School')
    now = timezone.now()
    School.objects.all().update(
        status='active',
        activated_at=now,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0006_guardians_alert_enabled'),
    ]

    operations = [
        migrations.AddField(
            model_name='school',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('active', 'Active'),
                    ('suspended', 'Suspended'),
                    ('archived', 'Archived'),
                ],
                db_index=True,
                default='active',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='school',
            name='region',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='school',
            name='category',
            field=models.CharField(
                blank=True,
                choices=[
                    ('creche', 'Creche'),
                    ('nursery', 'Nursery'),
                    ('kindergarten', 'Kindergarten'),
                    ('primary', 'Primary'),
                    ('jhs', 'Junior High School'),
                    ('shs', 'Senior High School'),
                    ('mixed', 'Mixed levels'),
                    ('other', 'Other'),
                ],
                default='',
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name='school',
            name='activated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='school',
            name='suspended_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(mark_existing_schools_active, migrations.RunPython.noop),
    ]
