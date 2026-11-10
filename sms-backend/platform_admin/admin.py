from django.contrib import admin

from platform_admin.models import (
    PlatformAuditLog,
    PlatformSettings,
    PlatformUser,
    SchoolAdminInvite,
)


@admin.register(PlatformUser)
class PlatformUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'role', 'is_active', 'mfa_enabled', 'created_at')
    list_filter = ('role', 'is_active', 'mfa_enabled')
    search_fields = ('email', 'first_name', 'last_name')
    readonly_fields = ('mfa_secret', 'created_at', 'updated_at')


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'public_school_registration_enabled',
        'subscription_grace_days',
        'updated_at',
    )


@admin.register(PlatformAuditLog)
class PlatformAuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'actor', 'target_type', 'target_id', 'created_at')
    list_filter = ('action',)
    search_fields = ('action', 'target_id', 'actor__email')
    readonly_fields = (
        'actor',
        'action',
        'target_type',
        'target_id',
        'detail',
        'ip_address',
        'created_at',
        'updated_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SchoolAdminInvite)
class SchoolAdminInviteAdmin(admin.ModelAdmin):
    list_display = (
        'school',
        'phone_number',
        'email',
        'status',
        'expires_at',
        'created_at',
    )
    list_filter = ('status',)
    search_fields = ('phone_number', 'email', 'school__name', 'token')
    readonly_fields = ('token', 'accepted_at', 'accepted_user', 'created_at', 'updated_at')

