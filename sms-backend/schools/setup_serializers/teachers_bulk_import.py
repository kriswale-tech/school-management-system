from rest_framework import serializers


class TeacherBulkImportPreviewRowSerializer(serializers.Serializer):
    row_number = serializers.IntegerField()
    status = serializers.ChoiceField(choices=['valid', 'error', 'warning'])
    messages = serializers.ListField(child=serializers.CharField())
    data = serializers.DictField()


class TeacherBulkImportPreviewSummarySerializer(serializers.Serializer):
    rows_total = serializers.IntegerField()
    rows_valid = serializers.IntegerField()
    rows_with_errors = serializers.IntegerField()
    rows_with_warnings = serializers.IntegerField()
    teachers_to_create = serializers.IntegerField()
    teachers_to_update = serializers.IntegerField()
    teachers_to_link = serializers.IntegerField(
        help_text='Teachers already in the system who will be given access to this school.',
    )
    assignments_to_create = serializers.IntegerField()
    assignments_to_replace = serializers.IntegerField()


class TeacherBulkImportConfirmSummarySerializer(serializers.Serializer):
    rows_total = serializers.IntegerField(required=False)
    rows_processed = serializers.IntegerField()
    rows_succeeded = serializers.IntegerField()
    rows_failed = serializers.IntegerField()
    teachers_created = serializers.IntegerField()
    teachers_updated = serializers.IntegerField()
    teachers_linked = serializers.IntegerField(
        help_text='Teachers already in the system who were given access to this school.',
    )
    assignments_created = serializers.IntegerField()
    assignments_replaced = serializers.IntegerField()


class TeacherBulkImportFailuresSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    download_url = serializers.CharField()
    expires_at = serializers.DateTimeField()
    format = serializers.ChoiceField(choices=['xlsx', 'csv'])


class TeacherBulkImportPreviewResponseSerializer(serializers.Serializer):
    dry_run = serializers.BooleanField()
    summary = TeacherBulkImportPreviewSummarySerializer()
    rows = TeacherBulkImportPreviewRowSerializer(many=True)


class TeacherBulkImportConfirmResponseSerializer(serializers.Serializer):
    dry_run = serializers.BooleanField()
    summary = TeacherBulkImportConfirmSummarySerializer()
    failures = TeacherBulkImportFailuresSerializer(allow_null=True)
