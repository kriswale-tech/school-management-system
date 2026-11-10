import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='PlatformSettings',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'public_school_registration_enabled',
                    models.BooleanField(
                        default=True,
                        help_text='When false, public school admin signup is disabled.',
                    ),
                ),
                (
                    'subscription_grace_days',
                    models.PositiveIntegerField(
                        default=7,
                        help_text='Days after a failed/overdue payment before suspension.',
                    ),
                ),
            ],
            options={
                'verbose_name_plural': 'Platform settings',
            },
        ),
        migrations.CreateModel(
            name='PlatformUser',
            fields=[
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('first_name', models.CharField(blank=True, default='', max_length=150)),
                ('last_name', models.CharField(blank=True, default='', max_length=150)),
                (
                    'role',
                    models.CharField(
                        choices=[
                            ('super_admin', 'Super Admin'),
                            ('operations', 'Platform Operations'),
                            ('finance', 'Finance Admin'),
                            ('support', 'Support Admin'),
                            ('curriculum', 'Curriculum Admin'),
                        ],
                        default='operations',
                        max_length=32,
                    ),
                ),
                ('is_active', models.BooleanField(default=True)),
                ('mfa_enabled', models.BooleanField(default=False)),
                ('mfa_secret', models.CharField(blank=True, default='', max_length=64)),
            ],
            options={
                'ordering': ['email'],
            },
        ),
        migrations.CreateModel(
            name='PlatformAuditLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('action', models.CharField(max_length=100)),
                ('target_type', models.CharField(blank=True, default='', max_length=100)),
                ('target_id', models.CharField(blank=True, default='', max_length=64)),
                ('detail', models.JSONField(blank=True, default=dict)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                (
                    'actor',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='audit_logs',
                        to='platform_admin.platformuser',
                    ),
                ),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='platformauditlog',
            index=models.Index(fields=['action', '-created_at'], name='platform_ad_action_6d0c0a_idx'),
        ),
        migrations.AddIndex(
            model_name='platformauditlog',
            index=models.Index(fields=['target_type', 'target_id'], name='platform_ad_target__b8f2d1_idx'),
        ),
    ]
