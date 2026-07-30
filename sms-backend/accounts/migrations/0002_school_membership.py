import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

BATCH_SIZE = 500


def backfill_memberships(apps, schema_editor):
    """Give every existing user a membership for the school they belonged to."""
    User = apps.get_model('accounts', 'User')
    SchoolMembership = apps.get_model('accounts', 'SchoolMembership')

    memberships = [
        SchoolMembership(
            user_id=user.pk,
            school_id=user.school_id,
            role=user.role,
            is_active=user.is_active,
        )
        for user in User.objects.all().iterator(chunk_size=BATCH_SIZE)
        if user.school_id
    ]

    SchoolMembership.objects.bulk_create(memberships, batch_size=BATCH_SIZE)


class Migration(migrations.Migration):
    """Splits identity from school access.

    Not reversible: rolling back would have to re-add User.school as a
    non-nullable column and pick one school for users who now have several.
    """

    dependencies = [
        ('accounts', '0001_initial'),
        ('schools', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SchoolMembership',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('role', models.CharField(choices=[('admin', 'Admin'), ('teacher', 'Teacher'), ('accountant', 'Accountant'), ('staff', 'Staff')], max_length=50)),
                ('is_active', models.BooleanField(default=True, verbose_name='active in this school')),
                ('last_active_at', models.DateTimeField(blank=True, null=True, verbose_name='last acted in this school at')),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='schools.school')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': [models.OrderBy(models.F('last_active_at'), descending=True, nulls_last=True), 'school__name'],
                'indexes': [models.Index(fields=['school', 'role'], name='accounts_sc_school__05acd2_idx')],
                'constraints': [models.UniqueConstraint(fields=('user', 'school'), name='unique_membership_per_user_and_school')],
            },
        ),
        migrations.RunPython(backfill_memberships, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='user',
            name='role',
        ),
        migrations.RemoveField(
            model_name='user',
            name='school',
        ),
    ]
