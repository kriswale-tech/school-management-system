import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('platform_admin', '0002_alter_platformuser_managers_and_more'),
        ('schools', '0007_school_lifecycle'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SchoolAdminInvite',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('phone_number', models.CharField(max_length=15)),
                ('email', models.EmailField(max_length=254)),
                ('first_name', models.CharField(max_length=150)),
                ('last_name', models.CharField(blank=True, default='', max_length=150)),
                ('token', models.CharField(db_index=True, max_length=64, unique=True)),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('pending', 'Pending'),
                            ('accepted', 'Accepted'),
                            ('expired', 'Expired'),
                            ('revoked', 'Revoked'),
                        ],
                        db_index=True,
                        default='pending',
                        max_length=20,
                    ),
                ),
                ('expires_at', models.DateTimeField()),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                (
                    'accepted_user',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='accepted_school_admin_invites',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'created_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='school_invites_created',
                        to='platform_admin.platformuser',
                    ),
                ),
                (
                    'school',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='admin_invites',
                        to='schools.school',
                    ),
                ),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='schooladmininvite',
            index=models.Index(fields=['school', 'status'], name='platform_ad_school__invite_idx'),
        ),
    ]
