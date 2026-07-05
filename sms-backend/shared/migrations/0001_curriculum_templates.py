import uuid

import django.db.models.deletion
from django.db import migrations, models


def seed_ghana_curriculum(apps, schema_editor):
    from shared.services.curriculum import seed_ghana_curriculum as seed

    seed()


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Curriculum',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('code', models.SlugField(max_length=50, unique=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='CurriculumLevel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('order', models.PositiveSmallIntegerField(default=1)),
                ('curriculum', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='levels', to='shared.curriculum')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='shared.curriculumlevel')),
            ],
            options={
                'ordering': ['order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='CurriculumClassLevel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('order', models.PositiveSmallIntegerField(default=1)),
                ('level', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='class_levels', to='shared.curriculumlevel')),
            ],
            options={
                'ordering': ['order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='CurriculumSubject',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('order', models.PositiveSmallIntegerField(default=1)),
                ('level', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subjects', to='shared.curriculumlevel')),
            ],
            options={
                'ordering': ['order', 'name'],
            },
        ),
        migrations.AddConstraint(
            model_name='curriculumlevel',
            constraint=models.UniqueConstraint(fields=('curriculum', 'parent', 'name'), name='unique_curriculum_level_name'),
        ),
        migrations.AddConstraint(
            model_name='curriculumclasslevel',
            constraint=models.UniqueConstraint(fields=('level', 'name'), name='unique_curriculum_class_level_name'),
        ),
        migrations.AddConstraint(
            model_name='curriculumsubject',
            constraint=models.UniqueConstraint(fields=('level', 'name'), name='unique_curriculum_subject_name'),
        ),
        migrations.RunPython(seed_ghana_curriculum, migrations.RunPython.noop),
    ]
