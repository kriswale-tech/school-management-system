from django.contrib import admin

from migration.models import (
    MappingProfile,
    MigrationAuditEvent,
    MigrationCommitRecord,
    MigrationFile,
    MigrationJob,
    MigrationRow,
    MigrationSheet,
)


class MigrationFileInline(admin.TabularInline):
    model = MigrationFile
    extra = 0
    fields = ('original_filename', 'file_hash', 'status', 'error')
    readonly_fields = fields


@admin.register(MigrationJob)
class MigrationJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'school', 'job_type', 'status', 'created_by', 'created_at')
    list_filter = ('job_type', 'status')
    inlines = [MigrationFileInline]


admin.site.register(MigrationSheet)
admin.site.register(MappingProfile)
admin.site.register(MigrationRow)
admin.site.register(MigrationCommitRecord)
admin.site.register(MigrationAuditEvent)
