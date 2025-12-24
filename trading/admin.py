from django.contrib import admin
from django.utils.html import format_html
from .models import (
    UserProfile,
    SubscriptionPackage,
    UserTradeAccount,
    TradeTransaction,
    SubscriptionPayment,
    BotAPIKey,
    BotStrategy,
    BacktestResult
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
        'active_bot',
        'balance_display',
        'subscription_expiry'
    ]
    list_filter = ['subscription_status', 'bot_status', 'broker_name', 'is_active', 'created_at']
    search_fields = ['account_name', 'user__username', 'mt5_account_id', 'broker_name']
    readonly_fields = ['created_at', 'updated_at', 'last_sync_datetime']
    raw_id_fields = ['user', 'subscription_package', 'active_bot']
    date_hierarchy = 'subscription_expiry'
    ordering = ['-created_at']

    fieldsets = (
        ('Account Information', {
            'fields': ('user', 'account_name', 'mt5_account_id', 'mt5_password', 'broker_name', 'mt5_server', 'current_balance', 'peak_balance')
        }),
        ('Subscription Details', {
            'fields': ('subscription_package', 'subscription_start', 'subscription_expiry', 'subscription_status')
        }),
        ('Bot Configuration', {
            'fields': ('bot_status', 'active_bot', 'bot_activated_at', 'trade_config')
        }),
        ('Drawdown Protection', {
            'fields': ('dd_blocked', 'dd_block_reason', 'dd_blocked_at'),
            'classes': ('collapse',)
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
        'bot_strategy',
        'symbol',
        'position_type',
        'position_status',
        'close_reason',
        'lot_size',
        'pnl_display',
        'comment',
        'opened_at',
        'closed_at'
    ]
    list_filter = ['position_status', 'position_type', 'close_reason', 'bot_strategy', 'symbol', 'opened_at']
    search_fields = ['mt5_order_id', 'symbol', 'trade_account__account_name', 'trade_account__user__username', 'bot_strategy__name', 'comment']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['trade_account', 'bot_strategy']
    date_hierarchy = 'opened_at'
    ordering = ['-opened_at']

    fieldsets = (
        ('Trade Information', {
            'fields': ('trade_account', 'bot_strategy', 'mt5_order_id', 'symbol', 'position_type', 'position_status', 'close_reason', 'comment')
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
        pnl_value = f'{obj.profit_loss:,.2f}'
        return format_html(
            '<span style="color: {}; font-weight: bold;">฿{}</span>',
            color,
            pnl_value
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
        amount_value = f'{obj.payment_amount:,.2f}'
        return format_html(
            '<span style="color: {}; font-weight: bold;">฿{}</span>',
            color,
            amount_value
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


@admin.register(BotStrategy)
class BotStrategyAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'version',
        'status',
        'strategy_type',
        'bot_strategy_class',
        'is_pair_trading',
        'backtest_range_days',
        'last_backtest_date',
        'is_active',
        'created_at'
    ]
    list_filter = ['status', 'strategy_type', 'bot_strategy_class', 'is_pair_trading', 'is_active', 'created_at', 'last_backtest_date']
    search_fields = ['name', 'description', 'strategy_type', 'bot_strategy_class', 'version']
    readonly_fields = ['created_at', 'updated_at', 'last_backtest_date', 'last_optimization_date']
    filter_horizontal = ['allowed_packages']
    ordering = ['-created_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'status', 'version', 'strategy_type', 'bot_strategy_class', 'is_pair_trading')
        }),
        ('Configuration', {
            'fields': ('allowed_symbols', 'allowed_packages', 'backtest_range_days'),
            'description': 'For single trading: ["EURUSD", "GBPUSD"]. For pair trading: ["EURUSD/GBPUSD", "AUDUSD/NZDUSD"]'
        }),
        ('Optimization & Parameters', {
            'fields': ('optimization_config', 'current_parameters'),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': ('last_backtest_date', 'last_optimization_date')
        }),
        ('System Information', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(BacktestResult)
class BacktestResultAdmin(admin.ModelAdmin):
    list_display = [
        'bot_strategy',
        'run_date',
        'date_range',
        'total_trades',
        'win_rate_display',
        'total_profit_display',
        'max_drawdown_display',
        'is_latest',
        'is_active'
    ]
    list_filter = ['is_latest', 'is_active', 'run_date', 'bot_strategy__status']
    search_fields = ['bot_strategy__name']
    readonly_fields = ['created_at', 'updated_at', 'equity_curve_preview', 'comprehensive_analysis_preview', 'trading_graph_preview']
    raw_id_fields = ['bot_strategy']
    date_hierarchy = 'run_date'
    ordering = ['-run_date']

    fieldsets = (
        ('Backtest Information', {
            'fields': ('bot_strategy', 'run_date', 'backtest_start_date', 'backtest_end_date', 'is_latest')
        }),
        ('Trade Statistics', {
            'fields': ('total_trades', 'winning_trades', 'losing_trades', 'win_rate')
        }),
        ('Profit Metrics', {
            'fields': ('total_profit', 'avg_profit_per_trade', 'best_trade', 'worst_trade')
        }),
        ('Risk Metrics', {
            'fields': ('max_drawdown', 'max_drawdown_percent')
        }),
        ('Visual Results', {
            'fields': (
                'equity_curve_image', 'equity_curve_preview',
                'comprehensive_analysis_image', 'comprehensive_analysis_preview',
                'trading_graph_image', 'trading_graph_preview'
            )
        }),
        ('Additional Data', {
            'fields': ('raw_data',),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def date_range(self, obj):
        return f"{obj.backtest_start_date} to {obj.backtest_end_date}"
    date_range.short_description = 'Test Period'

    def win_rate_display(self, obj):
        color = 'green' if obj.win_rate >= 50 else 'orange' if obj.win_rate >= 40 else 'red'
        win_rate_formatted = f'{obj.win_rate:.2f}'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>',
            color,
            win_rate_formatted
        )
    win_rate_display.short_description = 'Win Rate'

    def total_profit_display(self, obj):
        color = 'green' if obj.total_profit >= 0 else 'red'
        profit_formatted = f'{float(obj.total_profit):,.2f}'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            profit_formatted
        )
    total_profit_display.short_description = 'Total Profit'

    def max_drawdown_display(self, obj):
        drawdown_formatted = f'{float(obj.max_drawdown):,.2f}'
        drawdown_pct_formatted = f'{float(obj.max_drawdown_percent):.2f}'
        return format_html(
            '<span style="color: red;">{} ({}%)</span>',
            drawdown_formatted,
            drawdown_pct_formatted
        )
    max_drawdown_display.short_description = 'Max Drawdown'

    def equity_curve_preview(self, obj):
        if obj.equity_curve_image:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width: 400px; max-height: 300px;"/></a>',
                obj.equity_curve_image.url,
                obj.equity_curve_image.url
            )
        return "No equity curve image"
    equity_curve_preview.short_description = 'Equity Curve Preview'

    def comprehensive_analysis_preview(self, obj):
        if obj.comprehensive_analysis_image:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width: 400px; max-height: 300px;"/></a>',
                obj.comprehensive_analysis_image.url,
                obj.comprehensive_analysis_image.url
            )
        return "No comprehensive analysis image"
    comprehensive_analysis_preview.short_description = 'Comprehensive Analysis Preview'

    def trading_graph_preview(self, obj):
        if obj.trading_graph_image:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width: 400px; max-height: 300px;"/></a>',
                obj.trading_graph_image.url,
                obj.trading_graph_image.url
            )
        return "No trading graph image"
    trading_graph_preview.short_description = 'Trading Graph Preview'

