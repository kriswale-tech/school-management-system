from rest_framework import serializers


class StudentBulkImportPreviewRowSerializer(serializers.Serializer):
    row_number = serializers.IntegerField()
    status = serializers.ChoiceField(choices=['valid', 'error', 'warning'])
    messages = serializers.ListField(child=serializers.CharField())
    data = serializers.DictField()


class StudentBulkImportPreviewSummarySerializer(serializers.Serializer):
    rows_total = serializers.IntegerField()
    rows_valid = serializers.IntegerField()
    rows_with_errors = serializers.IntegerField()
    rows_with_warnings = serializers.IntegerField()
    students_to_create = serializers.IntegerField()
    guardians_to_link = serializers.IntegerField()


class StudentBulkImportConfirmSummarySerializer(serializers.Serializer):
    rows_total = serializers.IntegerField(required=False)
    rows_processed = serializers.IntegerField()
    rows_succeeded = serializers.IntegerField()
    rows_failed = serializers.IntegerField()
    students_created = serializers.IntegerField()
    guardians_linked = serializers.IntegerField()


class StudentBulkImportFailuresSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    download_url = serializers.CharField()
    expires_at = serializers.DateTimeField()
    format = serializers.ChoiceField(choices=['xlsx', 'csv'])


class StudentBulkImportPreviewResponseSerializer(serializers.Serializer):
    dry_run = serializers.BooleanField()
    summary = StudentBulkImportPreviewSummarySerializer()
    rows = StudentBulkImportPreviewRowSerializer(many=True)


class StudentBulkImportConfirmResponseSerializer(serializers.Serializer):
    dry_run = serializers.BooleanField()
    summary = StudentBulkImportConfirmSummarySerializer()
    failures = StudentBulkImportFailuresSerializer(allow_null=True)
