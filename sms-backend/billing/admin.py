from django.contrib import admin

from billing.models import (
    Invoice,
    InvoiceLine,
    Payment,
    Plan,
    PromotionCampaign,
    PromotionRedemption,
    SchoolSubscription,
    SubscriptionPeriod,
    TopUpPackage,
    TopUpPurchase,
)


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    readonly_fields = ('kind', 'description', 'quantity', 'unit_price_ghs', 'amount_ghs', 'metadata')


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'name',
        'student_min',
        'student_max',
        'price_monthly_ghs',
        'price_annual_ghs',
        'sort_order',
        'is_active',
    )
    list_filter = ('is_active',)
    search_fields = ('code', 'name')
    ordering = ('sort_order',)


@admin.register(SchoolSubscription)
class SchoolSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'school',
        'plan',
        'interval',
        'status',
        'is_current',
        'current_period_end',
        'created_at',
    )
    list_filter = ('status', 'interval', 'is_current')
    search_fields = ('school__name', 'plan__code', 'plan_code_snapshot')
    raw_id_fields = ('school', 'plan', 'pending_plan')


@admin.register(SubscriptionPeriod)
class SubscriptionPeriodAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'starts_at', 'ends_at', 'plan', 'interval')
    raw_id_fields = ('subscription', 'plan', 'invoice')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'school',
        'status',
        'total_ghs',
        'currency',
        'period_start',
        'period_end',
        'paid_at',
        'created_at',
    )
    list_filter = ('status', 'currency')
    search_fields = ('school__name', 'id')
    inlines = [InvoiceLineInline]
    raw_id_fields = ('school', 'subscription')


@admin.register(PromotionCampaign)
class PromotionCampaignAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'name',
        'discount_percent',
        'schedule',
        'audience',
        'billing_interval',
        'applies_to',
        'duration_months',
        'is_active',
    )
    list_filter = ('is_active', 'schedule', 'audience', 'applies_to')
    search_fields = ('code', 'name')
    filter_horizontal = ('schools',)


@admin.register(PromotionRedemption)
class PromotionRedemptionAdmin(admin.ModelAdmin):
    list_display = (
        'school',
        'campaign',
        'schedule',
        'discount_percent',
        'starts_at',
        'ends_at',
        'revoked_at',
        'created_at',
    )
    raw_id_fields = ('school', 'campaign', 'subscription')


@admin.register(TopUpPackage)
class TopUpPackageAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'name',
        'channel',
        'credits',
        'discount_percent',
        'price_ghs',
        'sort_order',
        'is_active',
    )
    list_filter = ('channel', 'is_active')
    search_fields = ('code', 'name')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'reference',
        'school',
        'purpose',
        'status',
        'amount_ghs',
        'provider',
        'paid_at',
        'created_at',
    )
    list_filter = ('status', 'purpose', 'provider')
    search_fields = ('reference', 'school__name', 'provider_transaction_id')
    raw_id_fields = ('school', 'invoice')


@admin.register(TopUpPurchase)
class TopUpPurchaseAdmin(admin.ModelAdmin):
    list_display = (
        'school',
        'package',
        'channel',
        'credits',
        'amount_ghs',
        'status',
        'created_at',
    )
    list_filter = ('channel', 'status')
    raw_id_fields = ('school', 'package', 'invoice', 'payment', 'ledger_entry')
