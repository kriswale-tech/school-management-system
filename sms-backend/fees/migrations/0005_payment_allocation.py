import uuid

import django.db.models.deletion
from django.db import migrations, models


def backfill_payment_allocations(apps, schema_editor):
    Payment = apps.get_model('fees', 'Payment')
    PaymentAllocation = apps.get_model('fees', 'PaymentAllocation')
    to_create = []
    for payment in Payment.objects.all().iterator():
        to_create.append(
            PaymentAllocation(
                id=uuid.uuid4(),
                payment_id=payment.id,
                term_id=payment.term_id,
                amount=payment.amount,
            ),
        )
        if len(to_create) >= 500:
            PaymentAllocation.objects.bulk_create(to_create)
            to_create = []
    if to_create:
        PaymentAllocation.objects.bulk_create(to_create)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('fees', '0004_student_fee_credit'),
        ('schools', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentAllocation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    'payment',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='allocations',
                        to='fees.payment',
                    ),
                ),
                (
                    'term',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='payment_allocations',
                        to='schools.term',
                    ),
                ),
            ],
            options={
                'ordering': ['term__start_date', 'created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='paymentallocation',
            constraint=models.CheckConstraint(
                condition=models.Q(('amount__gt', 0)),
                name='payment_allocation_amount_positive',
            ),
        ),
        migrations.AddConstraint(
            model_name='paymentallocation',
            constraint=models.UniqueConstraint(
                fields=('payment', 'term'),
                name='unique_payment_allocation_per_term',
            ),
        ),
        migrations.RunPython(backfill_payment_allocations, noop_reverse),
    ]
