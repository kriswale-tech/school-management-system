import re

from django.db import migrations, models


def _school_initials(name: str) -> str:
    words = re.findall(r'[A-Za-z0-9]+', name or '')
    if not words:
        return 'SCH'
    initials = ''.join(word[0].upper() for word in words)
    return initials[:6] or 'SCH'


def backfill_staff_ids(apps, schema_editor):
    School = apps.get_model('schools', 'School')
    SchoolMembership = apps.get_model('accounts', 'SchoolMembership')

    for school in School.objects.all().iterator():
        prefix = (school.student_id_prefix or '').strip().upper() or _school_initials(school.name)
        pattern = f'{prefix}-S'
        memberships = list(
            SchoolMembership.objects.filter(school_id=school.pk).order_by('created_at', 'id')
        )
        max_n = 0
        pending = []
        for membership in memberships:
            staff_id = (membership.staff_id or '').strip()
            if staff_id.startswith(pattern):
                suffix = staff_id[len(pattern):]
                if suffix.isdigit():
                    max_n = max(max_n, int(suffix))
            if not staff_id:
                pending.append(membership)

        for membership in pending:
            max_n += 1
            membership.staff_id = f'{pattern}{max_n:04d}'
            membership.save(update_fields=['staff_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_user_manager'),
        ('schools', '0008_curriculum_adoption'),
    ]

    operations = [
        migrations.AddField(
            model_name='schoolmembership',
            name='staff_id',
            field=models.CharField(
                blank=True,
                default='',
                help_text='School identification number. Blank values are filled on save.',
                max_length=255,
            ),
        ),
        migrations.RunPython(backfill_staff_ids, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='schoolmembership',
            constraint=models.UniqueConstraint(
                fields=('school', 'staff_id'),
                name='unique_staff_id_per_school',
            ),
        ),
    ]
