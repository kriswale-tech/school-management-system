from django.db import migrations, models
import django.db.models.deletion

import fees.storage


class Migration(migrations.Migration):

    dependencies = [
        ('fees', '0008_receipt_pdf'),
        ('schools', '0001_initial'),
        ('students', '0002_student_enrollment_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='FeeScheduleDocument',
            fields=[
                ('id', models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('file', models.FileField(blank=True, max_length=500, storage=fees.storage.receipt_storage, upload_to=fees.storage.fee_schedule_upload_to)),
                ('content_hash', models.CharField(blank=True, default='', max_length=64)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fee_schedule_documents', to='students.student')),
                ('term', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fee_schedule_documents', to='schools.term')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddConstraint(
            model_name='feescheduledocument',
            constraint=models.UniqueConstraint(fields=('student', 'term'), name='unique_fee_schedule_document_per_term'),
        ),
    ]
