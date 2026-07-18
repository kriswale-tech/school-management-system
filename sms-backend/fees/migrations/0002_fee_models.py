import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def clear_fee_stub_rows(apps, schema_editor):
    for model_name in ('Receipt', 'Payment', 'StudentFee', 'FeeItem', 'FeeStructure'):
        apps.get_model('fees', model_name).objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('fees', '0001_initial'),
        ('schools', '0001_initial'),
        ('students', '0002_student_enrollment_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(clear_fee_stub_rows, migrations.RunPython.noop),
        migrations.AddField(
            model_name='feestructure',
            name='applied_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='feestructure',
            name='created_by',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='created_fee_structures',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='feestructure',
            name='name',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='feestructure',
            name='published_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='feestructure',
            name='school',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='fee_structures',
                to='schools.school',
            ),
        ),
        migrations.AddField(
            model_name='feestructure',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('published', 'Published'),
                    ('applied', 'Applied'),
                    ('carried_forward', 'Carried Forward'),
                ],
                default='draft',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='feestructure',
            name='term',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='fee_structures',
                to='schools.term',
            ),
        ),
        migrations.AddField(
            model_name='feeitem',
            name='amount',
            field=models.DecimalField(decimal_places=2, max_digits=10),
        ),
        migrations.AddField(
            model_name='feeitem',
            name='applies_to_id',
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='feeitem',
            name='applies_to_type',
            field=models.CharField(
                choices=[('level', 'Level'), ('class', 'Class'), ('school', 'School')],
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='feeitem',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='feeitem',
            name='fee_structure',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='fee_items',
                to='fees.feestructure',
            ),
        ),
        migrations.AddField(
            model_name='feeitem',
            name='name',
            field=models.CharField(max_length=255),
        ),
        migrations.AddField(
            model_name='feeitem',
            name='student_type',
            field=models.CharField(
                choices=[
                    ('new_student', 'New Student'),
                    ('continuing_student', 'Continuing Student'),
                    ('all_students', 'All Students'),
                ],
                default='all_students',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='studentfee',
            name='amount',
            field=models.DecimalField(decimal_places=2, max_digits=10),
        ),
        migrations.AddField(
            model_name='studentfee',
            name='fee_item',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='student_fees',
                to='fees.feeitem',
            ),
        ),
        migrations.AddField(
            model_name='studentfee',
            name='fee_structure',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='student_fees',
                to='fees.feestructure',
            ),
        ),
        migrations.AddField(
            model_name='studentfee',
            name='name',
            field=models.CharField(max_length=255),
        ),
        migrations.AddField(
            model_name='studentfee',
            name='student',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='student_fees',
                to='students.student',
            ),
        ),
        migrations.AddField(
            model_name='studentfee',
            name='term',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='student_fees',
                to='schools.term',
            ),
        ),
        migrations.AddField(
            model_name='payment',
            name='amount',
            field=models.DecimalField(decimal_places=2, max_digits=10),
        ),
        migrations.AddField(
            model_name='payment',
            name='paid_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='payment',
            name='payment_method',
            field=models.CharField(
                choices=[
                    ('cash', 'Cash'),
                    ('cheque', 'Cheque'),
                    ('bank_transfer', 'Bank Transfer'),
                    ('mobile_money', 'Mobile Money'),
                    ('other', 'Other'),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='payment',
            name='payment_notes',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='payment',
            name='payment_reference',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='payment',
            name='recorded_by',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='recorded_payments',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='payment',
            name='student',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='payments',
                to='students.student',
            ),
        ),
        migrations.AddField(
            model_name='payment',
            name='term',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='payments',
                to='schools.term',
            ),
        ),
        migrations.AddField(
            model_name='receipt',
            name='issued_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='receipt',
            name='issued_by',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='issued_receipts',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='receipt',
            name='payment',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='receipt',
                to='fees.payment',
            ),
        ),
        migrations.AddField(
            model_name='receipt',
            name='receipt_number',
            field=models.CharField(max_length=50, unique=True),
        ),
        migrations.AddConstraint(
            model_name='feestructure',
            constraint=models.UniqueConstraint(
                fields=('school', 'term'),
                name='unique_fee_structure_per_school_and_term',
            ),
        ),
        migrations.AddConstraint(
            model_name='studentfee',
            constraint=models.UniqueConstraint(
                fields=('student', 'fee_item'),
                name='unique_student_fee_per_fee_item',
            ),
        ),
    ]
