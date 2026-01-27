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


class RequestType(models.TextChoices):
    PURCHASE = 'PURCHASE', 'New Purchase'
    RENEWAL = 'RENEWAL', 'Renewal'
    MT5_RESET = 'MT5_RESET', 'MT5 Account Reset'


class BotStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    PAUSED = 'PAUSED', 'Paused'
    DOWN = 'DOWN', 'Server Down'


class BotStrategyStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    INACTIVE = 'INACTIVE', 'Inactive'
    BETA = 'BETA', 'Beta'


class DDBlockReason(models.TextChoices):
    DAILY_DD_LIMIT = 'DAILY_DD_LIMIT', 'Daily DD Limit Reached'
    MAX_ACCOUNT_DD = 'MAX_ACCOUNT_DD', 'Max Account DD Reached'


class AccountType(models.TextChoices):
    PRO = 'PRO', 'Pro (No Suffix)'
    STANDARD = 'STANDARD', 'Standard'
    CENT = 'CENT', 'Cent'


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
    
    # Referral configuration
    referral_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Percentage of package price as credit for referrer (e.g., 20.00 for 20%)"
    )
    
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
    allow_dynamic_position_sizing = models.BooleanField(
        default=False,
        help_text="Allow dynamic position sizing based on risk percentage"
    )
    
    # Multi-account support
    max_accounts = models.PositiveIntegerField(
        default=1,
        help_text="Maximum number of trading accounts allowed per package (0 = unlimited)"
    )
    
    # MT5 reset rate limit
    mt5_reset_allowed_per_period = models.PositiveIntegerField(
        default=1,
        help_text="Number of MT5 account resets allowed per subscription period"
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
    
    # Symbol suffix configuration
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.PRO,
        help_text="Account type determines symbol suffix pattern"
    )
    symbol_suffix = models.CharField(
        max_length=10,
        blank=True,
        default='',
        help_text="Symbol suffix (e.g., 'm' for Standard, 'c' for Cent, empty for Pro)"
    )
    
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
    peak_balance = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Peak account balance"
    )
    
    # Drawdown protection status
    dd_blocked = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether bot is blocked due to drawdown protection"
    )
    dd_block_reason = models.CharField(
        max_length=20,
        choices=DDBlockReason.choices,
        null=True,
        blank=True,
        help_text="Reason for DD block"
    )
    dd_blocked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the bot was blocked by DD protection"
    )
    
    # MT5 reset tracking
    current_period_reset_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of MT5 resets in current subscription period"
    )
    last_mt5_reset_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time MT5 account details were reset"
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
    bot_strategy = models.ForeignKey(
        'BotStrategy',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trades',
        help_text="Bot that created this trade"
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
    
    # Comment field from MT5
    comment = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Comment field from MT5 trade (e.g., '5_MeanReversion_EURUSD')"
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
        related_name='payments',
        null=True,
        blank=True,
        help_text="Trade account (null for initial purchase before MT5 setup)"
    )
    subscription_package = models.ForeignKey(
        SubscriptionPackage,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    
    # Referral code used for this payment (optional)
    referral_code = models.ForeignKey(
        'ReferralCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='used_in_payments',
        help_text="Referral code used in this purchase"
    )
    
    # Request type
    request_type = models.CharField(
        max_length=20,
        choices=RequestType.choices,
        default=RequestType.PURCHASE,
        help_text="Type of request: new purchase, renewal, or MT5 reset"
    )
    
    # New MT5 data for reset requests
    new_mt5_data = models.JSONField(
        null=True,
        blank=True,
        help_text="New MT5 account details for reset requests (account_name, mt5_account_id, mt5_password, mt5_server, broker_name)"
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
        help_text="Strategy type (e.g., Trend Following, Mean Reversion, Scalping, Correlation Divergence)"
    )
    bot_strategy_class = models.CharField(
        max_length=100,
        blank=True,
        help_text="Bot strategy class name (e.g., TrendFollowingBot, CorrelationDivergenceBot)"
    )
    
    # Pair trading support
    is_pair_trading = models.BooleanField(
        default=False,
        help_text="Whether this strategy trades symbol pairs (e.g., EURUSD/GBPUSD)"
    )
    
    # Allowed configurations
    allowed_symbols = models.JSONField(
        default=list,
        blank=True,
        help_text="List of trading symbols. For single: ['XAUUSD', 'EURUSD']. For pairs: ['EURUSD/GBPUSD', 'AUDUSD/NZDUSD']"
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
        pair_indicator = " (Pair)" if self.is_pair_trading else ""
        return f"{self.name} v{self.version}{pair_indicator} ({self.get_status_display()})"
    
    def get_latest_backtest(self):
        """Get the most recent backtest result"""
        return self.backtest_results.filter(is_latest=True).first()
    
    def validate_symbol_format(self, symbol):
        """
        Validate if a symbol matches the strategy type.
        For pair trading: expects "SYMBOL1/SYMBOL2" format
        For single trading: expects single symbol format
        """
        if self.is_pair_trading:
            # Pair trading expects format like "EURUSD/GBPUSD"
            return '/' in symbol and len(symbol.split('/')) == 2
        else:
            # Single symbol should not have '/'
            return '/' not in symbol
    
    def parse_symbol_pair(self, symbol_pair):
        """
        Parse a symbol pair into its components.
        Returns tuple (symbol1, symbol2) or (symbol, None) for single symbols.
        """
        if self.is_pair_trading and '/' in symbol_pair:
            parts = symbol_pair.split('/')
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
        return symbol_pair, None
    
    def get_all_unique_symbols(self):
        """
        Get all unique symbols from allowed_symbols.
        For pair trading, extracts individual symbols from pairs.
        """
        unique_symbols = set()
        for symbol in self.allowed_symbols:
            if self.is_pair_trading and '/' in symbol:
                s1, s2 = self.parse_symbol_pair(symbol)
                unique_symbols.add(s1)
                if s2:
                    unique_symbols.add(s2)
            else:
                unique_symbols.add(symbol)
        return list(unique_symbols)


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


# User Package Quota Model
class UserPackageQuota(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='package_quotas')
    subscription_package = models.ForeignKey(
        SubscriptionPackage,
        on_delete=models.PROTECT,
        related_name='user_quotas'
    )
    
    # Quota tracking
    quota_total = models.PositiveIntegerField(
        help_text="Total number of accounts allowed by this quota"
    )
    accounts_used = models.PositiveIntegerField(
        default=0,
        help_text="Number of accounts currently using this quota"
    )
    
    # Validity period
    start_date = models.DateTimeField(
        help_text="When this quota becomes active"
    )
    expiry_date = models.DateTimeField(
        db_index=True,
        help_text="When this quota expires"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.ACTIVE,
        db_index=True
    )
    
    class Meta:
        verbose_name = 'User Package Quota'
        verbose_name_plural = 'User Package Quotas'
        ordering = ['-expiry_date']
        indexes = [
            models.Index(fields=['user', 'status', '-expiry_date']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.subscription_package.name} ({self.accounts_used}/{self.quota_total})"
    
    def has_available_slots(self):
        """Check if there are available account slots"""
        return self.accounts_used < self.quota_total
    
    def get_remaining_slots(self):
        """Get number of remaining account slots"""
        return max(0, self.quota_total - self.accounts_used)


# Referral Code Model
class ReferralCode(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='referral_code')
    code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Unique referral code for the user"
    )
    
    # Marketing campaign configuration
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Promotional discount percentage for referred friends (e.g., 10.00 for 10%)"
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Marketing description or campaign name for this referral code"
    )
    
    class Meta:
        verbose_name = 'Referral Code'
        verbose_name_plural = 'Referral Codes'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.code}"
    
    def get_promotion_text(self):
        """Get readable promotion description"""
        if self.discount_percentage > 0:
            return f"Get {self.discount_percentage:.0f}% discount" + (f" - {self.description}" if self.description else "")
        return self.description or "No promotion"


# Referral Earnings Model
class ReferralEarnings(TimeStampedModel):
    referrer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='referral_earnings'
    )
    referee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='referred_by_earnings',
        help_text="User who was referred"
    )
    referral_code = models.ForeignKey(
        ReferralCode,
        on_delete=models.PROTECT,
        related_name='earnings'
    )
    subscription_payment = models.ForeignKey(
        SubscriptionPayment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referral_earnings'
    )
    subscription_package = models.ForeignKey(
        SubscriptionPackage,
        on_delete=models.PROTECT,
        related_name='referral_earnings'
    )
    
    # Earnings details
    package_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Original package price at time of purchase"
    )
    referral_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Percentage rate applied"
    )
    credit_earned = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Credit amount earned by referrer"
    )
    
    # Tracking
    is_recurring = models.BooleanField(
        default=False,
        help_text="Whether this is a recurring monthly credit"
    )
    month_number = models.PositiveIntegerField(
        default=1,
        help_text="Which month this earning is for (1=first month, 2=second, etc.)"
    )
    
    class Meta:
        verbose_name = 'Referral Earning'
        verbose_name_plural = 'Referral Earnings'
        ordering = ['-created_at']
        unique_together = [['referrer', 'referee', 'subscription_payment']]

    def __str__(self):
        return f"{self.referrer.username} <- {self.referee.username} (฿{self.credit_earned})"


# User Credit Balance Model
class UserCredit(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='credit_balance')
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Available credit balance in THB"
    )
    
    class Meta:
        verbose_name = 'User Credit'
        verbose_name_plural = 'User Credits'

    def __str__(self):
        return f"{self.user.username} - ฿{self.balance}"
    
    def add_credit(self, amount, description=""):
        """Add credit to balance and create transaction"""
        self.balance += amount
        self.save()
        ReferralTransaction.objects.create(
            user=self.user,
            transaction_type='CREDIT',
            amount=amount,
            description=description or "Credit added"
        )
        return self.balance
    
    def deduct_credit(self, amount, description=""):
        """Deduct credit from balance and create transaction"""
        if self.balance >= amount:
            self.balance -= amount
            self.save()
            ReferralTransaction.objects.create(
                user=self.user,
                transaction_type='DEBIT',
                amount=amount,
                description=description or "Credit used"
            )
            return True
        return False


# Referral Transaction Ledger
class ReferralTransaction(TimeStampedModel):
    TRANSACTION_TYPES = [
        ('CREDIT', 'Credit Added'),
        ('DEBIT', 'Credit Used'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referral_transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    
    # Related objects
    referral_earning = models.ForeignKey(
        ReferralEarnings,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    subscription_payment = models.ForeignKey(
        SubscriptionPayment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='credit_transactions'
    )
    
    class Meta:
        verbose_name = 'Referral Transaction'
        verbose_name_plural = 'Referral Transactions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} ฿{self.amount}"
