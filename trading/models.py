from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal


# Abstract base model for timestamps and soft delete
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        abstract = True


# Choices for various status fields
class PositionType(models.TextChoices):
    BUY = 'BUY', 'Buy'
    SELL = 'SELL', 'Sell'


class PositionStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    CLOSED = 'CLOSED', 'Closed'
    PENDING = 'PENDING', 'Pending'


class CloseReason(models.TextChoices):
    MANUAL = 'MANUAL', 'Manual'
    TAKE_PROFIT = 'TP', 'TP'
    STOP_LOSS = 'SL', 'SL'
    MARGIN_CALL = 'MARGIN_CALL', 'Margin Call'


class SubscriptionStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    EXPIRED = 'EXPIRED', 'Expired'
    CANCELLED = 'CANCELLED', 'Cancelled'
    PENDING = 'PENDING', 'Pending'


class PaymentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'
    REFUNDED = 'REFUNDED', 'Refunded'


class BotStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    PAUSED = 'PAUSED', 'Paused'
    DOWN = 'DOWN', 'Server Down'


class BotStrategyStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    INACTIVE = 'INACTIVE', 'Inactive'
    BETA = 'BETA', 'Beta'


# User Profile Model
class UserProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    line_uuid = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    line_display_name = models.CharField(max_length=200, blank=True)
    line_picture_url = models.URLField(max_length=500, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.first_name} {self.last_name}"
    
    def is_line_connected(self):
        """Check if LINE account is connected"""
        return self.line_uuid and not self.line_uuid.startswith('temp_')


# Subscription Package Model
class SubscriptionPackage(TimeStampedModel):
    name = models.CharField(max_length=100)
    duration_days = models.PositiveIntegerField(help_text="Package duration in days")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price in THB")
    features = models.JSONField(default=dict, blank=True, help_text="Package features as JSON")
    description = models.TextField(blank=True)
    
    # Symbol pair limits
    max_symbols = models.PositiveIntegerField(
        default=1,
        help_text="Maximum number of trading symbol pairs allowed (0 = unlimited)"
    )
    
    # Lot size limits
    min_lot_size = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.01'),
        help_text="Minimum lot size allowed"
    )
    max_lot_size = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.01'),
        null=True,
        blank=True,
        help_text="Maximum lot size allowed (null = unlimited)"
    )
    
    # Feature flags
    allow_news_filter = models.BooleanField(
        default=False,
        help_text="Allow automatic bot pause during high-impact news events"
    )
    allow_dd_protection = models.BooleanField(
        default=False,
        help_text="Allow drawdown protection configuration"
    )

    class Meta:
        verbose_name = 'Subscription Package'
        verbose_name_plural = 'Subscription Packages'
        ordering = ['price']

    def __str__(self):
        return f"{self.name} - {self.duration_days} days - ฿{self.price}"
    
    def is_lot_size_valid(self, lot_size):
        """Check if lot size is within package limits"""
        if lot_size < self.min_lot_size:
            return False
        if self.max_lot_size and lot_size > self.max_lot_size:
            return False
        return True
    
    def get_max_symbols_display(self):
        """Get display text for max symbols"""
        if self.max_symbols == 0:
            return "Unlimited"
        return str(self.max_symbols)


# User Trade Account Model
class UserTradeAccount(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trade_accounts')
    account_name = models.CharField(max_length=200)
    mt5_account_id = models.CharField(max_length=100, help_text="MT5 Account Number")
    mt5_password = models.CharField(max_length=200, blank=True, help_text="MT5 Account Password (encrypted)")
    broker_name = models.CharField(max_length=100)
    mt5_server = models.CharField(max_length=100)
    
    # Subscription details
    subscription_package = models.ForeignKey(
        SubscriptionPackage, 
        on_delete=models.PROTECT, 
        related_name='subscribed_accounts'
    )
    subscription_start = models.DateTimeField(db_index=True)
    subscription_expiry = models.DateTimeField(db_index=True)
    subscription_status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.PENDING,
        db_index=True
    )
    
    # Bot configuration and status
    bot_status = models.CharField(
        max_length=20,
        choices=BotStatus.choices,
        default=BotStatus.PAUSED,
        db_index=True
    )
    trade_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Trading configuration: lot_size, timeframes (M5, M15), notification_settings"
    )
    
    # Bot strategy assignment
    active_bot = models.ForeignKey(
        'BotStrategy',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_accounts',
        help_text="Currently assigned bot strategy"
    )
    bot_activated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the bot was activated for this account"
    )
    
    # Sync tracking
    last_sync_datetime = models.DateTimeField(null=True, blank=True)
    
    # Account balance tracking
    current_balance = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Current account balance"
    )

    class Meta:
        verbose_name = 'User Trade Account'
        verbose_name_plural = 'User Trade Accounts'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'mt5_account_id'],
                name='unique_user_mt5_account'
            )
        ]

    def __str__(self):
        return f"{self.account_name} - {self.mt5_account_id} ({self.user.username})"


# Trade Transaction Model
class TradeTransaction(TimeStampedModel):
    trade_account = models.ForeignKey(
        UserTradeAccount,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    
    # MT5 order details
    mt5_order_id = models.BigIntegerField(db_index=True, help_text="MT5 Order Ticket Number")
    symbol = models.CharField(max_length=20, db_index=True, help_text="Trading symbol (e.g., EURUSD)")
    
    # Position details
    position_type = models.CharField(
        max_length=10,
        choices=PositionType.choices,
        default=PositionType.BUY
    )
    position_status = models.CharField(
        max_length=20,
        choices=PositionStatus.choices,
        default=PositionStatus.OPEN,
        db_index=True
    )
    
    # Timing
    opened_at = models.DateTimeField(db_index=True)
    closed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Close reason
    close_reason = models.CharField(
        max_length=20,
        choices=CloseReason.choices,
        null=True,
        blank=True,
        help_text="Reason for closing the position"
    )
    
    # Prices
    entry_price = models.DecimalField(max_digits=19, decimal_places=4)
    exit_price = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    take_profit = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    stop_loss = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    
    # Volume and financials
    lot_size = models.DecimalField(max_digits=10, decimal_places=2)
    profit_loss = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Profit/Loss amount"
    )
    commission = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=Decimal('0.0000')
    )
    swap_fee = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=Decimal('0.0000')
    )
    
    # Account balance at close
    account_balance_at_close = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Account balance when position was closed"
    )

    class Meta:
        verbose_name = 'Trade Transaction'
        verbose_name_plural = 'Trade Transactions'
        ordering = ['-opened_at']
        indexes = [
            models.Index(fields=['trade_account', '-opened_at']),
            models.Index(fields=['symbol', 'opened_at']),
            models.Index(fields=['position_status', '-opened_at']),
        ]

    def __str__(self):
        return f"{self.mt5_order_id} - {self.symbol} {self.position_type} ({self.position_status})"


# Subscription Payment Model
class SubscriptionPayment(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    trade_account = models.ForeignKey(
        UserTradeAccount,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    subscription_package = models.ForeignKey(
        SubscriptionPackage,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    
    # Payment details
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount in THB")
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    payment_method = models.CharField(max_length=50, blank=True, help_text="e.g., PromptPay, Bank Transfer")
    transaction_reference = models.CharField(max_length=200, blank=True, help_text="Payment reference or transaction ID")
    payment_date = models.DateTimeField(default=timezone.now)
    
    # Payment slip upload
    payment_slip = models.ImageField(
        upload_to='payment_slips/%Y/%m/',
        null=True,
        blank=True,
        help_text="Upload payment slip image"
    )
    
    # Admin notes
    admin_notes = models.TextField(blank=True, help_text="Admin verification notes")
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_payments'
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Subscription Payment'
        verbose_name_plural = 'Subscription Payments'
        ordering = ['-payment_date']

    def __str__(self):
        return f"{self.user.username} - ฿{self.payment_amount} ({self.payment_status})"


# Bot API Key Model (Master key for MT5 bot system)
class BotAPIKey(TimeStampedModel):
    key = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Master API key for bot authentication"
    )
    name = models.CharField(
        max_length=100,
        help_text="Descriptive name for this API key"
    )
    last_used = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time this API key was used"
    )

    class Meta:
        verbose_name = 'Bot API Key'
        verbose_name_plural = 'Bot API Keys'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({'Active' if self.is_active else 'Inactive'})"


# Bot Strategy Model
class BotStrategy(TimeStampedModel):
    name = models.CharField(max_length=200, help_text="Bot strategy name")
    description = models.TextField(blank=True, help_text="Detailed description of the bot strategy")
    status = models.CharField(
        max_length=20,
        choices=BotStrategyStatus.choices,
        default=BotStrategyStatus.INACTIVE,
        db_index=True,
        help_text="Bot availability status"
    )
    version = models.CharField(max_length=50, default="1.0.0", help_text="Bot version")
    strategy_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Strategy type (e.g., Trend Following, Mean Reversion, Scalping)"
    )
    
    # Allowed configurations
    allowed_symbols = models.JSONField(
        default=list,
        blank=True,
        help_text="List of trading symbols this bot supports (e.g., ['XAUUSD', 'EURUSD'])"
    )
    allowed_packages = models.ManyToManyField(
        SubscriptionPackage,
        related_name='bot_strategies',
        blank=True,
        help_text="Subscription packages that can use this bot"
    )
    
    # Optimization and backtest configuration
    optimization_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Optimization settings: lookback_days, threshold_points, tp_sl_ranges, parameter_ranges"
    )
    current_parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Current optimized parameters for the bot strategy"
    )
    backtest_range_days = models.PositiveIntegerField(
        default=90,
        help_text="Number of days to backtest"
    )
    
    # Tracking
    last_backtest_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time backtest was run"
    )
    last_optimization_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time optimization was run"
    )

    class Meta:
        verbose_name = 'Bot Strategy'
        verbose_name_plural = 'Bot Strategies'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} v{self.version} ({self.get_status_display()})"
    
    def get_latest_backtest(self):
        """Get the most recent backtest result"""
        return self.backtest_results.filter(is_latest=True).first()


# Backtest Result Model
class BacktestResult(TimeStampedModel):
    bot_strategy = models.ForeignKey(
        BotStrategy,
        on_delete=models.CASCADE,
        related_name='backtest_results',
        help_text="Bot strategy this backtest is for"
    )
    
    # Backtest timing
    run_date = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When this backtest was run"
    )
    backtest_start_date = models.DateField(help_text="Start date of backtest period")
    backtest_end_date = models.DateField(help_text="End date of backtest period")
    
    # Trade statistics
    total_trades = models.PositiveIntegerField(default=0, help_text="Total number of trades")
    winning_trades = models.PositiveIntegerField(default=0, help_text="Number of winning trades")
    losing_trades = models.PositiveIntegerField(default=0, help_text="Number of losing trades")
    win_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Win rate percentage"
    )
    
    # Profit metrics
    total_profit = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Total profit/loss"
    )
    avg_profit_per_trade = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Average profit per trade"
    )
    best_trade = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Best single trade profit"
    )
    worst_trade = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Worst single trade loss"
    )
    
    # Risk metrics
    max_drawdown = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Maximum drawdown amount"
    )
    max_drawdown_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Maximum drawdown percentage"
    )
    
    # Visual results
    equity_curve_image = models.ImageField(
        upload_to='backtest_curves/%Y/%m/',
        null=True,
        blank=True,
        help_text="Equity curve chart image"
    )
    comprehensive_analysis_image = models.ImageField(
        upload_to='backtest_analysis/%Y/%m/',
        null=True,
        blank=True,
        help_text="Comprehensive analysis chart (Monte Carlo, Walk Forward)"
    )
    trading_graph_image = models.ImageField(
        upload_to='backtest_trades/%Y/%m/',
        null=True,
        blank=True,
        help_text="Backtest trading graph showing entry/exit points"
    )
    
    # Additional data
    raw_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional backtest data (trade list, daily returns, etc.)"
    )
    
    # Flag for latest result
    is_latest = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this is the most recent backtest result for the strategy"
    )

    class Meta:
        verbose_name = 'Backtest Result'
        verbose_name_plural = 'Backtest Results'
        ordering = ['-run_date']
        indexes = [
            models.Index(fields=['bot_strategy', '-run_date']),
            models.Index(fields=['is_latest', '-run_date']),
        ]

    def __str__(self):
        return f"{self.bot_strategy.name} - {self.run_date.strftime('%Y-%m-%d')} ({'Latest' if self.is_latest else 'Historical'})"

