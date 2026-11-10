from django.contrib import admin

from communications.models import (
    CommunicationAddonSku,
    CreditAccount,
    CreditLedgerEntry,
    EmailPricingConfig,
    MessagingAllowancePolicy,
    ProviderAccount,
    ProviderBalanceSnapshot,
    ProviderExpense,
    ProviderPurchase,
    ProviderReconciliationItem,
    ProviderReconciliationRun,
    ResendUsageSnapshot,
    SmsEncodingConfig,
)


@admin.register(CommunicationAddonSku)
class CommunicationAddonSkuAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'name',
        'channel',
        'interval',
        'credits_per_period',
        'price_ghs',
        'is_active',
    )
    list_filter = ('channel', 'interval', 'is_active')
    search_fields = ('code', 'name')


@admin.register(CreditAccount)
class CreditAccountAdmin(admin.ModelAdmin):
    list_display = ('school', 'channel', 'balance', 'updated_at')
    list_filter = ('channel',)
    search_fields = ('school__name',)
    raw_id_fields = ('school',)


@admin.register(CreditLedgerEntry)
class CreditLedgerEntryAdmin(admin.ModelAdmin):
    list_display = (
        'school',
        'channel',
        'entry_type',
        'delta',
        'balance_after',
        'occurred_at',
    )
    list_filter = ('channel', 'entry_type')
    search_fields = ('school__name', 'idempotency_key')
    readonly_fields = (
        'school',
        'channel',
        'entry_type',
        'delta',
        'balance_after',
        'idempotency_key',
        'occurred_at',
        'subscription_period',
        'invoice',
        'guardian_delivery',
        'actor_platform_user',
        'metadata',
        'created_at',
        'updated_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SmsEncodingConfig)
class SmsEncodingConfigAdmin(admin.ModelAdmin):
    list_display = (
        'encoding',
        'single_segment_limit',
        'multipart_segment_limit',
        'provider_cost_per_segment_ghs',
        'school_price_per_segment_ghs',
        'is_active',
        'effective_from',
    )
    list_filter = ('encoding', 'is_active')


@admin.register(EmailPricingConfig)
class EmailPricingConfigAdmin(admin.ModelAdmin):
    list_display = (
        'school_price_per_credit_ghs',
        'estimated_provider_cost_per_email_ghs',
        'is_active',
        'effective_from',
    )
    list_filter = ('is_active',)


@admin.register(ProviderAccount)
class ProviderAccountAdmin(admin.ModelAdmin):
    list_display = ('provider', 'channel', 'display_name', 'api_status', 'last_synced_at')
    list_filter = ('provider', 'channel', 'api_status')


@admin.register(ProviderBalanceSnapshot)
class ProviderBalanceSnapshotAdmin(admin.ModelAdmin):
    list_display = ('provider_account', 'sms_balance', 'captured_at', 'source')
    list_filter = ('source',)


@admin.register(ResendUsageSnapshot)
class ResendUsageSnapshotAdmin(admin.ModelAdmin):
    list_display = ('provider_account', 'monthly_used', 'monthly_limit', 'captured_at')


@admin.register(ProviderPurchase)
class ProviderPurchaseAdmin(admin.ModelAdmin):
    list_display = (
        'provider',
        'channel',
        'amount_ghs',
        'credits_or_units',
        'effective_cost_per_unit',
        'purchased_at',
    )
    list_filter = ('provider', 'channel')


@admin.register(ProviderExpense)
class ProviderExpenseAdmin(admin.ModelAdmin):
    list_display = ('provider', 'expense_kind', 'amount_ghs', 'period_start', 'period_end')
    list_filter = ('provider', 'expense_kind')


@admin.register(MessagingAllowancePolicy)
class MessagingAllowancePolicyAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'scope',
        'school',
        'channel',
        'classification',
        'monthly_free_units',
        'is_active',
    )
    list_filter = ('scope', 'channel', 'classification', 'is_active')


@admin.register(ProviderReconciliationRun)
class ProviderReconciliationRunAdmin(admin.ModelAdmin):
    list_display = (
        'provider',
        'channel',
        'status',
        'matched_count',
        'discrepancy_count',
        'started_at',
    )
    list_filter = ('provider', 'status')


@admin.register(ProviderReconciliationItem)
class ProviderReconciliationItemAdmin(admin.ModelAdmin):
    list_display = (
        'run',
        'discrepancy_type',
        'resolution',
        'provider_message_id',
        'created_at',
    )
    list_filter = ('discrepancy_type', 'resolution', 'provider')
