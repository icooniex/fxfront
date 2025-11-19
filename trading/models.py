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


# User Profile Model
class UserProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    line_uuid = models.CharField(max_length=100, unique=True, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.first_name} {self.last_name}"


# Subscription Package Model
class SubscriptionPackage(TimeStampedModel):
    name = models.CharField(max_length=100)
    duration_days = models.PositiveIntegerField(help_text="Package duration in days")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price in THB")
    features = models.JSONField(default=dict, blank=True, help_text="Package features as JSON")
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Subscription Package'
        verbose_name_plural = 'Subscription Packages'
        ordering = ['price']

    def __str__(self):
        return f"{self.name} - {self.duration_days} days - ฿{self.price}"


# User Trade Account Model
class UserTradeAccount(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trade_accounts')
    account_name = models.CharField(max_length=200)
    mt5_account_id = models.CharField(max_length=100, help_text="MT5 Account Number")
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

