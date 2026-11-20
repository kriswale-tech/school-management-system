from rest_framework import serializers

from migration.models import (
    MappingProfile,
    MigrationFile,
    MigrationJob,
    MigrationRow,
    MigrationSheet,
    MigrationTransform,
)
from migration.services.mapping import mapping_payload
from migration.targets import fields_for


class MigrationSheetSerializer(serializers.ModelSerializer):
    mappings = serializers.SerializerMethodField()

    class Meta:
        model = MigrationSheet
        fields = [
            'id',
            'sheet_name',
            'header_row',
            'detected_headers',
            'sample_rows',
            'row_count',
            'included',
            'mapping_profile',
            'mappings',
        ]

    def get_mappings(self, sheet):
        mappings = sheet.field_mappings.prefetch_related('transforms').order_by('position')
        return mapping_payload(mappings)


class MigrationFileSerializer(serializers.ModelSerializer):
    sheets = MigrationSheetSerializer(many=True, read_only=True)

    class Meta:
        model = MigrationFile
        fields = [
            'id',
            'original_filename',
            'file_hash',
            'file_size',
            'detected_encoding',
            'detected_delimiter',
            'status',
            'error',
            'role',
            'sheets',
        ]


class MigrationJobSerializer(serializers.ModelSerializer):
    files = MigrationFileSerializer(many=True, read_only=True)

    class Meta:
        model = MigrationJob
        fields = [
            'id',
            'job_type',
            'template',
            'status',
            'source_system',
            'file_hash',
            'summary',
            'created_at',
            'committed_at',
            'files',
        ]
        read_only_fields = ['status', 'file_hash', 'summary', 'created_at', 'committed_at']

    def validate(self, attrs):
        template = attrs.get('template') or ''
        job_type = attrs.get('job_type')
        if template and template not in MigrationJob.Template.values:
            raise serializers.ValidationError({
                'template': 'Choose Student information, Enrollment history, Opening balances, or Fee history.',
            })
        if template in {
            MigrationJob.Template.OPENING_BALANCES,
            MigrationJob.Template.HISTORICAL_FINANCE,
        }:
            if job_type != MigrationJob.JobType.FEE_FINANCIAL_HISTORY:
                raise serializers.ValidationError({
                    'template': 'This import uses the fee import.',
                })
        elif template and job_type != MigrationJob.JobType.STUDENT_ENROLLMENT:
            raise serializers.ValidationError({'template': 'That template is only for student imports.'})
        return attrs


class MappingWriteSerializer(serializers.Serializer):
    source_column = serializers.CharField(max_length=255)
    target_field = serializers.CharField(max_length=64, allow_blank=True, required=False)
    ignored = serializers.BooleanField(required=False)
    transforms = serializers.ListField(child=serializers.DictField(), required=False)


class ProfileWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    source_system = serializers.CharField(max_length=120, allow_blank=True, required=False)
    mappings = MappingWriteSerializer(many=True)


class ProfileSerializer(serializers.ModelSerializer):
    mappings = serializers.SerializerMethodField()

    class Meta:
        model = MappingProfile
        fields = ['id', 'name', 'source_system', 'job_type', 'mappings', 'created_at']

    def get_mappings(self, profile):
        return mapping_payload(profile.field_mappings.prefetch_related('transforms'))


class MigrationRowSerializer(serializers.ModelSerializer):
    sheet_name = serializers.CharField(source='sheet.sheet_name', read_only=True)
    file_hash = serializers.CharField(source='sheet.migration_file.file_hash', read_only=True)

    class Meta:
        model = MigrationRow
        fields = [
            'id',
            'sheet_name',
            'file_hash',
            'source_row_number',
            'raw_values',
            'transformed_values',
            'validation_status',
            'commit_status',
            'errors',
            'warnings',
            'proposal',
        ]


def target_fields_for(job_type, template='', role=''):
    return [
        {'key': key, 'label': label, 'required': required}
        for key, label, required in fields_for(job_type, template, role)
    ]


def transform_choices():
    return [{'step': step, 'label': label} for step, label in MigrationTransform.Step.choices]
