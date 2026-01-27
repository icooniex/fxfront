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
    BacktestResult,
    UserPackageQuota,
    ReferralCode,
    ReferralEarnings,
    UserCredit,
    ReferralTransaction
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
    list_display = ['name', 'duration_days', 'price_display', 'max_accounts', 'mt5_reset_allowed_per_period', 'is_active', 'created_at']
    list_filter = ['is_active', 'duration_days', 'max_accounts']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['price']

    fieldsets = (
        ('Package Details', {
            'fields': ('name', 'duration_days', 'price', 'description', 'is_active')
        }),
        ('Referral Configuration', {
            'fields': ('referral_percentage',),
            'description': 'Percentage of package price earned as credit by referrers (e.g., 20.00 for 20%)'
        }),
        ('Account Limits', {
            'fields': ('max_accounts', 'max_symbols', 'min_lot_size', 'max_lot_size')
        }),
        ('Feature Flags', {
            'fields': ('allow_news_filter', 'allow_dd_protection', 'allow_dynamic_position_sizing')
        }),
        ('MT5 Reset Configuration', {
            'fields': ('mt5_reset_allowed_per_period',),
            'description': 'Number of MT5 account resets allowed per subscription period'
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

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
        'account_type',
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
            'fields': ('user', 'account_name', 'mt5_account_id', 'mt5_password', 'broker_name', 'mt5_server', 'account_type', 'symbol_suffix', 'current_balance', 'peak_balance')
        }),
        ('Subscription Details', {
            'fields': ('subscription_package', 'subscription_start', 'subscription_expiry', 'subscription_status')
        }),
        ('Bot Configuration', {
            'fields': ('bot_status', 'active_bot', 'bot_activated_at', 'trade_config')
        }),
        ('MT5 Reset Tracking', {
            'fields': ('current_period_reset_count', 'last_mt5_reset_at'),
            'classes': ('collapse',)
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
        'entry_price',
        'exit_price',
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
        'request_type_display',
        'amount_display',
        'payment_status',
        'payment_method',
        'payment_date',
        'slip_preview'
    ]
    list_filter = ['payment_status', 'request_type', 'payment_method', 'payment_date', 'is_active']
    search_fields = [
        'user__username',
        'trade_account__account_name',
        'transaction_reference',
        'subscription_package__name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'slip_preview', 'mt5_data_comparison']
    raw_id_fields = ['user', 'trade_account', 'subscription_package', 'verified_by']
    date_hierarchy = 'payment_date'
    ordering = ['-payment_date']

    fieldsets = (
        ('Payment Information', {
            'fields': ('user', 'trade_account', 'subscription_package', 'request_type', 'payment_amount', 'payment_status')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'transaction_reference', 'payment_date', 'payment_slip', 'slip_preview')
        }),
        ('MT5 Reset Data', {
            'fields': ('new_mt5_data', 'mt5_data_comparison'),
            'classes': ('collapse',),
            'description': 'Only applicable for MT5_RESET requests'
        }),
        ('Verification', {
            'fields': ('admin_notes', 'verified_by', 'verified_at')
        }),
        ('System Information', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def request_type_display(self, obj):
        colors = {
            'PURCHASE': '#3b82f6',  # blue
            'RENEWAL': '#22c55e',   # green
            'MT5_RESET': '#f59e0b'  # orange
        }
        color = colors.get(obj.request_type, '#6b7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">{}</span>',
            color,
            obj.get_request_type_display()
        )
    request_type_display.short_description = 'Request Type'

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
    
    def mt5_data_comparison(self, obj):
        """Show comparison between old and new MT5 data for reset requests"""
        if obj.request_type != 'MT5_RESET' or not obj.new_mt5_data or not obj.trade_account:
            return "N/A"
        
        account = obj.trade_account
        new_data = obj.new_mt5_data
        
        comparison = '<table style="width: 100%; border-collapse: collapse;">'
        comparison += '<tr style="background: #f3f4f6;"><th style="padding: 8px; text-align: left;">Field</th><th style="padding: 8px; text-align: left;">Current</th><th style="padding: 8px; text-align: left;">New</th></tr>'
        
        fields = [
            ('Account Name', account.account_name, new_data.get('account_name', '')),
            ('MT5 Account ID', account.mt5_account_id, new_data.get('mt5_account_id', '')),
            ('MT5 Password', '******', '******' if new_data.get('mt5_password') else ''),
            ('MT5 Server', account.mt5_server, new_data.get('mt5_server', '')),
            ('Broker Name', account.broker_name, new_data.get('broker_name', '')),
        ]
        
        for field_name, old_value, new_value in fields:
            changed = old_value != new_value
            row_style = 'background: #fef3c7;' if changed else ''
            comparison += f'<tr style="{row_style}"><td style="padding: 8px; font-weight: 600;">{field_name}</td><td style="padding: 8px;">{old_value}</td><td style="padding: 8px; color: #3b82f6; font-weight: 600;">{new_value}</td></tr>'
        
        comparison += '</table>'
        return format_html(comparison)
    mt5_data_comparison.short_description = 'MT5 Data Comparison'


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


@admin.register(UserPackageQuota)
class UserPackageQuotaAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'subscription_package',
        'quota_usage_display',
        'status',
        'start_date',
        'expiry_date',
        'days_remaining_display',
        'is_active'
    ]
    list_filter = ['status', 'is_active', 'subscription_package', 'start_date', 'expiry_date']
    search_fields = ['user__username', 'user__email', 'subscription_package__name']
    readonly_fields = ['created_at', 'updated_at', 'quota_progress_bar', 'related_accounts_display']
    raw_id_fields = ['user', 'subscription_package']
    date_hierarchy = 'expiry_date'
    ordering = ['-created_at']

    fieldsets = (
        ('User & Package', {
            'fields': ('user', 'subscription_package', 'status')
        }),
        ('Quota Information', {
            'fields': ('quota_total', 'accounts_used', 'quota_progress_bar')
        }),
        ('Subscription Period', {
            'fields': ('start_date', 'expiry_date')
        }),
        ('Related Accounts', {
            'fields': ('related_accounts_display',),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def quota_usage_display(self, obj):
        """Display quota usage with color coding"""
        percentage = (obj.accounts_used / obj.quota_total * 100) if obj.quota_total > 0 else 0
        
        if percentage >= 100:
            color = '#ef4444'  # red
        elif percentage >= 80:
            color = '#f59e0b'  # orange
        else:
            color = '#22c55e'  # green
            
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} / {}</span> <span style="color: #6b7280; font-size: 11px;">({}%)</span>',
            color,
            obj.accounts_used,
            obj.quota_total,
            int(percentage)
        )
    quota_usage_display.short_description = 'Quota Usage'

    def days_remaining_display(self, obj):
        """Display days remaining with color coding"""
        from django.utils import timezone
        from datetime import timedelta
        
        if obj.expiry_date:
            days = (obj.expiry_date - timezone.now()).days
            
            if days < 0:
                return format_html('<span style="color: #ef4444; font-weight: bold;">Expired</span>')
            elif days <= 7:
                return format_html('<span style="color: #f59e0b; font-weight: bold;">{} days</span>', days)
            else:
                return format_html('<span style="color: #22c55e;">{} days</span>', days)
        return '-'
    days_remaining_display.short_description = 'Days Remaining'

    def quota_progress_bar(self, obj):
        """Visual progress bar for quota usage"""
        percentage = (obj.accounts_used / obj.quota_total * 100) if obj.quota_total > 0 else 0
        
        if percentage >= 100:
            bar_color = '#ef4444'
        elif percentage >= 80:
            bar_color = '#f59e0b'
        else:
            bar_color = '#3b82f6'
            
        return format_html(
            '''
            <div style="width: 100%; background: #e5e7eb; border-radius: 10px; height: 20px; position: relative; overflow: hidden;">
                <div style="width: {}%; background: {}; height: 100%; border-radius: 10px; transition: width 0.3s;"></div>
                <span style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 11px; font-weight: 600; color: #1f2937;">
                    {} / {} accounts ({}%)
                </span>
            </div>
            ''',
            min(percentage, 100),
            bar_color,
            obj.accounts_used,
            obj.quota_total,
            int(percentage)
        )
    quota_progress_bar.short_description = 'Quota Progress'

    def related_accounts_display(self, obj):
        """Display all trade accounts created under this quota"""
        from django.utils import timezone
        
        accounts = UserTradeAccount.objects.filter(
            user=obj.user,
            subscription_package=obj.subscription_package,
            subscription_start__gte=obj.start_date,
            subscription_expiry__lte=obj.expiry_date,
            is_active=True
        ).order_by('-created_at')
        
        if not accounts.exists():
            return format_html('<em style="color: #6b7280;">No accounts created yet</em>')
        
        html = '<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">'
        html += '<tr style="background: #f3f4f6;"><th style="padding: 8px; text-align: left;">Account Name</th><th style="padding: 8px; text-align: left;">MT5 ID</th><th style="padding: 8px; text-align: left;">Status</th><th style="padding: 8px; text-align: left;">Created</th></tr>'
        
        for account in accounts:
            status_colors = {
                'ACTIVE': '#22c55e',
                'EXPIRED': '#ef4444',
                'PENDING': '#f59e0b',
                'SUSPENDED': '#6b7280'
            }
            status_color = status_colors.get(account.subscription_status, '#6b7280')
            
            html += f'''
            <tr>
                <td style="padding: 8px;"><a href="/admin/trading/usertradeaccount/{account.id}/change/" target="_blank">{account.account_name}</a></td>
                <td style="padding: 8px;">{account.mt5_account_id}</td>
                <td style="padding: 8px;"><span style="background: {status_color}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px;">{account.get_subscription_status_display()}</span></td>
                <td style="padding: 8px; color: #6b7280; font-size: 12px;">{account.created_at.strftime("%d/%m/%Y %H:%M")}</td>
            </tr>
            '''
        
        html += '</table>'
        return format_html(html)
    related_accounts_display.short_description = 'Related Trade Accounts'


# ============================================================================
# REFERRAL SYSTEM ADMIN
# ============================================================================

@admin.register(ReferralCode)
class ReferralCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'user_display', 'discount_percentage', 'description', 'is_active', 'created_at']
    list_filter = ['is_active', 'discount_percentage', 'created_at']
    search_fields = ['code', 'user__username', 'user__first_name', 'user__last_name', 'description']
    readonly_fields = ['code', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Referral Code', {
            'fields': ('user', 'code')
        }),
        ('Marketing Campaign', {
            'fields': ('discount_percentage', 'description'),
            'description': 'Configure promotional benefits for referred friends. Leave discount_percentage at 0.00 if no special promotion.'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_display(self, obj):
        return f"{obj.user.username} ({obj.user.first_name} {obj.user.last_name})"
    user_display.short_description = 'User'


@admin.register(ReferralEarnings)
class ReferralEarningsAdmin(admin.ModelAdmin):
    list_display = ['referrer', 'referee', 'package_name', 'credit_earned_display', 'is_recurring', 'created_at']
    list_filter = ['is_recurring', 'subscription_package', 'created_at']
    search_fields = ['referrer__username', 'referee__username', 'referral_code__code']
    readonly_fields = ['referrer', 'referee', 'referral_code', 'subscription_payment', 'package_price', 'referral_percentage', 'created_at', 'updated_at']
    raw_id_fields = ['referrer', 'referee']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Referral Information', {
            'fields': ('referrer', 'referee', 'referral_code')
        }),
        ('Earnings Details', {
            'fields': ('subscription_package', 'package_price', 'referral_percentage', 'credit_earned', 'is_recurring', 'month_number')
        }),
        ('Payment Reference', {
            'fields': ('subscription_payment',),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def package_name(self, obj):
        return obj.subscription_package.name
    package_name.short_description = 'Package'
    
    def credit_earned_display(self, obj):
        return f"฿{obj.credit_earned:,.2f}"
    credit_earned_display.short_description = 'Credit Earned'
    
    def has_add_permission(self, request):
        # Earnings are created automatically via signals, not manually
        return False


@admin.register(UserCredit)
class UserCreditAdmin(admin.ModelAdmin):
    list_display = ['user_display', 'balance_display', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['user', 'created_at', 'updated_at']
    ordering = ['-balance']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Credit Balance', {
            'fields': ('balance',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_display(self, obj):
        return f"{obj.user.username} ({obj.user.first_name} {obj.user.last_name})"
    user_display.short_description = 'User'
    
    def balance_display(self, obj):
        return f"฿{obj.balance:,.2f}"
    balance_display.short_description = 'Balance'
    
    def has_add_permission(self, request):
        # Credit accounts are created automatically for new users
        return False


@admin.register(ReferralTransaction)
class ReferralTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type_display', 'amount_display', 'description_short', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['user__username', 'description']
    readonly_fields = ['user', 'transaction_type', 'amount', 'description', 'referral_earning', 'subscription_payment', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Transaction Information', {
            'fields': ('user', 'transaction_type', 'amount', 'description')
        }),
        ('Related Objects', {
            'fields': ('referral_earning', 'subscription_payment'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def transaction_type_display(self, obj):
        if obj.transaction_type == 'CREDIT':
            return format_html('<span style="color: green; font-weight: bold;">+{}</span>', obj.get_transaction_type_display())
        else:
            return format_html('<span style="color: red; font-weight: bold;">-{}</span>', obj.get_transaction_type_display())
    transaction_type_display.short_description = 'Type'
    
    def amount_display(self, obj):
        symbol = '+' if obj.transaction_type == 'CREDIT' else '-'
        color = 'green' if obj.transaction_type == 'CREDIT' else 'red'
        amount_formatted = f'{float(obj.amount):,.2f}'
        return format_html('<span style="color: {}; font-weight: bold;">{}฿{}</span>', color, symbol, amount_formatted)
    amount_display.short_description = 'Amount'
    
    def description_short(self, obj):
        if len(obj.description) > 50:
            return obj.description[:50] + '...'
        return obj.description
    description_short.short_description = 'Description'
    
    def has_add_permission(self, request):
        # Transactions are created automatically via signals
        return False
