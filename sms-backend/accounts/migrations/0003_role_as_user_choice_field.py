import uuid

import django.db.models.deletion
from django.db import migrations, models

ROLE_CHOICES = [
    ('admin', 'Admin'),
    ('teacher', 'Teacher'),
    ('accountant', 'Accountant'),
    ('staff', 'Staff'),
]


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_permission_phoneotp_remove_user_username_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='role',
        ),
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.CharField(choices=ROLE_CHOICES, max_length=50),
        ),
        migrations.DeleteModel(
            name='RolePermission',
        ),
        migrations.DeleteModel(
            name='Role',
        ),
        migrations.CreateModel(
            name='RolePermission',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('role', models.CharField(choices=ROLE_CHOICES, max_length=50)),
                ('permission', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='role_permissions',
                    to='accounts.permission',
                )),
            ],
            options={
                'unique_together': {('role', 'permission')},
            },
        ),
    ]
