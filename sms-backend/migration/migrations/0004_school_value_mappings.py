import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0006_phase2_student_enrollment'),
        ('migration', '0003_standard_templates'),
        ('schools', '0008_curriculum_adoption'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SchoolValueMapping',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('field_name', models.CharField(max_length=64)),
                ('source_value', models.CharField(max_length=255)),
                ('source_label', models.CharField(blank=True, default='', max_length=255)),
                ('canonical_value', models.CharField(blank=True, default='', max_length=255)),
                ('origin', models.CharField(blank=True, default='manual', max_length=32)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='migration_value_mappings', to=settings.AUTH_USER_MODEL)),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='migration_value_mappings', to='schools.school')),
                ('stream', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='migration_value_mappings', to='academics.classstream')),
            ],
        ),
        migrations.AddConstraint(
            model_name='schoolvaluemapping',
            constraint=models.UniqueConstraint(fields=('school', 'field_name', 'source_value'), name='unique_school_migration_value'),
        ),
    ]
