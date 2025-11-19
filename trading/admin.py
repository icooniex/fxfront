from django.contrib import admin
from django.utils.html import format_html
from .models import (
    UserProfile,
    SubscriptionPackage,
    UserTradeAccount,
    TradeTransaction,
    SubscriptionPayment,
    BotAPIKey
)
import secrets


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'first_name', 'last_name', 'line_uuid', 'phone_number', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__username', 'first_name', 'last_name', 'line_uuid', 'phone_number']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(SubscriptionPackage)
class SubscriptionPackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'duration_days', 'price_display', 'is_active', 'created_at']
    list_filter = ['is_active', 'duration_days']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['price']

    def price_display(self, obj):
        return f"฿{obj.price:,.2f}"
    price_display.short_description = 'Price (THB)'


@admin.register(UserTradeAccount)
class UserTradeAccountAdmin(admin.ModelAdmin):
    list_display = [
        'account_name', 
        'user', 
        'mt5_account_id', 
        'broker_name',
        'subscription_status',
        'bot_status',
        'balance_display',
        'subscription_expiry'
    ]
    list_filter = ['subscription_status', 'bot_status', 'broker_name', 'is_active', 'created_at']
    search_fields = ['account_name', 'user__username', 'mt5_account_id', 'broker_name']
    readonly_fields = ['created_at', 'updated_at', 'last_sync_datetime']
    raw_id_fields = ['user', 'subscription_package']
    date_hierarchy = 'subscription_expiry'
    ordering = ['-created_at']

    fieldsets = (
        ('Account Information', {
            'fields': ('user', 'account_name', 'mt5_account_id', 'broker_name', 'mt5_server', 'current_balance')
        }),
        ('Subscription Details', {
            'fields': ('subscription_package', 'subscription_start', 'subscription_expiry', 'subscription_status')
        }),
        ('Bot Configuration', {
            'fields': ('bot_status', 'trade_config')
        }),
        ('System Information', {
            'fields': ('is_active', 'last_sync_datetime', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def balance_display(self, obj):
        return f"฿{obj.current_balance:,.2f}"
    balance_display.short_description = 'Current Balance'


@admin.register(TradeTransaction)
class TradeTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'mt5_order_id',
        'trade_account',
        'symbol',
        'position_type',
        'position_status',
        'lot_size',
        'pnl_display',
        'opened_at',
        'closed_at'
    ]
    list_filter = ['position_status', 'position_type', 'symbol', 'opened_at']
    search_fields = ['mt5_order_id', 'symbol', 'trade_account__account_name', 'trade_account__user__username']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['trade_account']
    date_hierarchy = 'opened_at'
    ordering = ['-opened_at']

    fieldsets = (
        ('Trade Information', {
            'fields': ('trade_account', 'mt5_order_id', 'symbol', 'position_type', 'position_status')
        }),
        ('Timing', {
            'fields': ('opened_at', 'closed_at')
        }),
        ('Prices', {
            'fields': ('entry_price', 'exit_price', 'take_profit', 'stop_loss')
        }),
        ('Financials', {
            'fields': ('lot_size', 'profit_loss', 'commission', 'swap_fee', 'account_balance_at_close')
        }),
        ('System Information', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def pnl_display(self, obj):
        color = 'green' if obj.profit_loss >= 0 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">฿{:,.2f}</span>',
            color,
            obj.profit_loss
        )
    pnl_display.short_description = 'P&L'


@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'trade_account',
        'subscription_package',
        'amount_display',
        'payment_status',
        'payment_method',
        'payment_date',
        'slip_preview'
    ]
    list_filter = ['payment_status', 'payment_method', 'payment_date', 'is_active']
    search_fields = [
        'user__username',
        'trade_account__account_name',
        'transaction_reference',
        'subscription_package__name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'slip_preview']
    raw_id_fields = ['user', 'trade_account', 'subscription_package', 'verified_by']
    date_hierarchy = 'payment_date'
    ordering = ['-payment_date']

    fieldsets = (
        ('Payment Information', {
            'fields': ('user', 'trade_account', 'subscription_package', 'payment_amount', 'payment_status')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'transaction_reference', 'payment_date', 'payment_slip', 'slip_preview')
        }),
        ('Verification', {
            'fields': ('admin_notes', 'verified_by', 'verified_at')
        }),
        ('System Information', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def amount_display(self, obj):
        color = 'green' if obj.payment_status == 'COMPLETED' else 'orange'
        return format_html(
            '<span style="color: {}; font-weight: bold;">฿{:,.2f}</span>',
            color,
            obj.payment_amount
        )
    amount_display.short_description = 'Amount (THB)'

    def slip_preview(self, obj):
        if obj.payment_slip:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width: 200px; max-height: 200px;"/></a>',
                obj.payment_slip.url,
                obj.payment_slip.url
            )
        return "No slip uploaded"
    slip_preview.short_description = 'Payment Slip Preview'


@admin.register(BotAPIKey)
class BotAPIKeyAdmin(admin.ModelAdmin):
    list_display = ['name', 'key_display', 'is_active', 'last_used', 'created_at']
    list_filter = ['is_active', 'created_at', 'last_used']
    search_fields = ['name', 'key']
    readonly_fields = ['key', 'created_at', 'updated_at', 'last_used']
    ordering = ['-created_at']
    
    fieldsets = [
        ('API Key Information', {
            'fields': ['name', 'key', 'is_active']
        }),
        ('Usage', {
            'fields': ['last_used'],
            'classes': ['collapse']
        }),
        ('System Information', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    def key_display(self, obj):
        """Show masked API key for security"""
        if obj.key:
            return f"{obj.key[:8]}...{obj.key[-8:]}"
        return "-"
    key_display.short_description = 'API Key'
    
    def save_model(self, request, obj, form, change):
        """Auto-generate API key on creation"""
        if not change:  # Only on creation
            obj.key = secrets.token_urlsafe(48)
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        """Make key readonly after creation"""
        if obj:  # Editing existing object
            return self.readonly_fields
        else:  # Creating new object
            return ['created_at', 'updated_at', 'last_used']

