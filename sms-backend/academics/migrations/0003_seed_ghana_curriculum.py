from django.db import migrations


def seed_ghana_curriculum(apps, schema_editor):
    from academics.services.curriculum import seed_ghana_curriculum as seed

    seed()


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0002_initial'),
    ]

    operations = [
        migrations.RunPython(seed_ghana_curriculum, migrations.RunPython.noop),
    ]
