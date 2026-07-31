import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0001_initial'),
        ('students', '0003_alter_student_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='Parent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('first_name', models.CharField(max_length=255)),
                ('last_name', models.CharField(max_length=255)),
                ('other_names', models.CharField(blank=True, default='', max_length=255)),
                ('phone_number', models.CharField(max_length=15)),
                ('phone_number_alt', models.CharField(blank=True, default='', max_length=15)),
                ('email', models.EmailField(blank=True, default='', max_length=254)),
                ('address', models.TextField(blank=True, default='')),
                (
                    'school',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='parents',
                        to='schools.school',
                    ),
                ),
            ],
            options={
                'ordering': ['last_name', 'first_name'],
            },
        ),
        migrations.AddField(
            model_name='student',
            name='admission_date',
            field=models.DateField(default='2000-01-01'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='student',
            name='date_of_birth',
            field=models.DateField(default='2000-01-01'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='student',
            name='gender',
            field=models.CharField(
                choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
                default='other',
                max_length=10,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='student',
            name='other_names',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.CreateModel(
            name='StudentParent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'relationship',
                    models.CharField(
                        choices=[
                            ('father', 'Father'),
                            ('mother', 'Mother'),
                            ('guardian', 'Guardian'),
                            ('other', 'Other'),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    'is_primary',
                    models.BooleanField(
                        default=False,
                        help_text='Primary contact for this student. Only one parent may be primary.',
                    ),
                ),
                ('is_emergency_contact', models.BooleanField(default=False)),
                (
                    'parent',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='student_links',
                        to='students.parent',
                    ),
                ),
                (
                    'student',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='parent_links',
                        to='students.student',
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name='student',
            name='parents',
            field=models.ManyToManyField(
                related_name='students',
                through='students.StudentParent',
                to='students.parent',
            ),
        ),
        migrations.AddConstraint(
            model_name='parent',
            constraint=models.UniqueConstraint(
                fields=('school', 'phone_number'),
                name='unique_parent_phone_per_school',
            ),
        ),
        migrations.AddConstraint(
            model_name='studentparent',
            constraint=models.UniqueConstraint(
                fields=('student', 'parent'),
                name='unique_student_parent_link',
            ),
        ),
        migrations.AddConstraint(
            model_name='studentparent',
            constraint=models.UniqueConstraint(
                condition=models.Q(('is_primary', True)),
                fields=('student',),
                name='unique_primary_parent_per_student',
            ),
        ),
    ]
