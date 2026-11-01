from django.contrib import admin

from notifications.models import GuardianDelivery, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'event_type',
        'title',
        'recipient',
        'school',
        'read_at',
        'created_at',
    )
    list_filter = ('event_type', 'email_status', 'school')
    search_fields = ('title', 'body', 'recipient__user__phone_number')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(GuardianDelivery)
class GuardianDeliveryAdmin(admin.ModelAdmin):
    list_display = (
        'event_type',
        'channel',
        'status',
        'parent',
        'student',
        'school',
        'created_at',
    )
    list_filter = ('event_type', 'channel', 'status', 'school')
    search_fields = (
        'parent__name',
        'parent__phone_number',
        'recipient_address',
        'provider_message_id',
        'idempotency_key',
    )
    readonly_fields = ('created_at', 'updated_at', 'idempotency_key')
