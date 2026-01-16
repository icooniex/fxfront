from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import (
    SubscriptionPayment, UserTradeAccount, PaymentStatus, 
    SubscriptionStatus, BotStrategy, RequestType
)
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=SubscriptionPayment)
def handle_payment_status_change(sender, instance, **kwargs):
    """
    Handle payment status changes and update trade account accordingly
    - PURCHASE: Send notification (trade_account created in separate MT5 setup step)
    - RENEWAL: Reset period counters and extend subscription
    - MT5_RESET: Update MT5 credentials and clear Redis keys
    - COMPLETED: Activate account and set subscription dates
    - FAILED: Keep account in PENDING status, allow re-upload
    - REFUNDED: Cancel account subscription
    """
    if not instance.pk:
        # New payment, skip
        return
    
    try:
        # Get the old payment status
        old_payment = SubscriptionPayment.objects.get(pk=instance.pk)
        old_status = old_payment.payment_status
        new_status = instance.payment_status
        
        # Only process if status actually changed
        if old_status == new_status:
            return
        
        # Handle COMPLETED status
        if new_status == PaymentStatus.COMPLETED and old_status != PaymentStatus.COMPLETED:
            # Set verified timestamp
            instance.verified_at = timezone.now()
            
            # Handle different request types
            if instance.request_type == RequestType.PURCHASE:
                # New purchase - trade_account will be created during MT5 setup
                # TODO: Send LINE/SMS notification with setup link
                logger.info(f"New purchase approved for user {instance.user.username}, waiting for MT5 setup")
                
            elif instance.request_type == RequestType.RENEWAL:
                # Renewal - extend existing account subscription
                trade_account = instance.trade_account
                if trade_account:
                    trade_account.subscription_status = SubscriptionStatus.ACTIVE
                    
                    # Reset MT5 reset counter for new period
                    trade_account.current_period_reset_count = 0
                    
                    # Extend from current expiry or start fresh
                    current_expiry = trade_account.subscription_expiry
                    if current_expiry and current_expiry > timezone.now():
                        # Still active, extend from current expiry
                        trade_account.subscription_expiry = current_expiry + timedelta(days=instance.subscription_package.duration_days)
                    else:
                        # Expired or no expiry, start fresh
                        trade_account.subscription_start = timezone.now()
                        trade_account.subscription_expiry = timezone.now() + timedelta(days=instance.subscription_package.duration_days)
                    
                    # Update package if changed (for upgrades/downgrades)
                    if trade_account.subscription_package != instance.subscription_package:
                        trade_account.subscription_package = instance.subscription_package
                    
                    trade_account.save(update_fields=[
                        'subscription_status', 'subscription_start', 'subscription_expiry', 
                        'subscription_package', 'current_period_reset_count', 'updated_at'
                    ])
                    logger.info(f"Renewed subscription for account {trade_account.mt5_account_id}")
                    
            elif instance.request_type == RequestType.MT5_RESET:
                # MT5 reset - update credentials with new data
                trade_account = instance.trade_account
                if trade_account and instance.new_mt5_data:
                    # Store old MT5 account ID for Redis cleanup
                    old_mt5_account_id = trade_account.mt5_account_id
                    
                    # Update MT5 fields from new_mt5_data
                    if 'account_name' in instance.new_mt5_data:
                        trade_account.account_name = instance.new_mt5_data['account_name']
                    if 'mt5_account_id' in instance.new_mt5_data:
                        trade_account.mt5_account_id = instance.new_mt5_data['mt5_account_id']
                    if 'mt5_password' in instance.new_mt5_data:
                        trade_account.mt5_password = instance.new_mt5_data['mt5_password']
                    if 'mt5_server' in instance.new_mt5_data:
                        trade_account.mt5_server = instance.new_mt5_data['mt5_server']
                    if 'broker_name' in instance.new_mt5_data:
                        trade_account.broker_name = instance.new_mt5_data['broker_name']
                    
                    # Increment reset counter
                    trade_account.current_period_reset_count += 1
                    trade_account.last_mt5_reset_at = timezone.now()
                    
                    # Force bot to PAUSED - admin must manually restart after MT5 setup
                    trade_account.bot_status = 'PAUSED'
                    
                    trade_account.save()
                    
                    # Clear old Redis keys if account ID changed
                    if old_mt5_account_id != trade_account.mt5_account_id:
                        try:
                            from trading.api.views import clear_redis_keys_for_account
                            clear_redis_keys_for_account(old_mt5_account_id)
                            logger.info(f"Cleared Redis keys for old account ID {old_mt5_account_id}")
                        except Exception as e:
                            logger.error(f"Failed to clear Redis keys: {e}")
                    
                    logger.info(f"MT5 reset completed for account {trade_account.account_name}")
            
        # Handle FAILED status - keep account in PENDING, allow re-upload
        elif new_status == PaymentStatus.FAILED:
            # Keep account status as PENDING so user can upload new slip
            if instance.trade_account and instance.trade_account.subscription_status == SubscriptionStatus.PENDING:
                pass  # No change needed, stays PENDING
            
        # Handle REFUNDED status
        elif new_status == PaymentStatus.REFUNDED:
            # Cancel the subscription
            if instance.trade_account:
                instance.trade_account.subscription_status = SubscriptionStatus.CANCELLED
                instance.trade_account.save(update_fields=['subscription_status', 'updated_at'])
            
    except SubscriptionPayment.DoesNotExist:
        pass


@receiver(post_save, sender=UserTradeAccount)
def handle_trade_account_update(sender, instance, created, update_fields, **kwargs):
    """
    Handle UserTradeAccount updates and update Redis versions accordingly.
    Triggers when trade_config, bot_status, or subscription_status changes.
    """
    if created:
        # New account, initialize Redis heartbeat
        try:
            from trading.api.views import update_server_heartbeat_in_redis, update_trade_config_version_in_redis
            update_server_heartbeat_in_redis(instance)
            update_trade_config_version_in_redis(instance.mt5_account_id, 1)
            logger.info(f"Initialized Redis for new account {instance.mt5_account_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Redis for new account: {e}")
        return
    
    # For existing accounts, update Redis
    try:
        from trading.api.views import update_server_heartbeat_in_redis, update_trade_config_version_in_redis
        
        # Always update server heartbeat
        update_server_heartbeat_in_redis(instance)
        
        # Check if important fields were updated
        if update_fields:
            important_fields = {'trade_config', 'bot_status', 'subscription_status', 'dd_blocked', 'active_bot'}
            if any(field in update_fields for field in important_fields):
                update_trade_config_version_in_redis(instance.mt5_account_id)
                logger.info(f"Incremented trade config version for account {instance.mt5_account_id}")
        else:
            # If update_fields is None, we don't know what changed, so increment version
            update_trade_config_version_in_redis(instance.mt5_account_id)
            logger.info(f"Incremented trade config version for account {instance.mt5_account_id}")
            
    except Exception as e:
        logger.error(f"Failed to update Redis for account {instance.mt5_account_id}: {e}")


@receiver(post_save, sender=BotStrategy)
def handle_bot_strategy_update(sender, instance, created, update_fields, **kwargs):
    """
    Handle BotStrategy updates and increment Redis strategy config versions.
    Triggers when current_parameters, status, or allowed_symbols changes.
    """
    if created:
        # New strategy, no need to update versions yet
        return
    
    try:
        from trading.api.views import update_strategy_config_version_in_redis
        
        # Check if important fields were updated
        should_increment_version = False
        
        if update_fields:
            important_fields = {'current_parameters', 'status', 'allowed_symbols'}
            should_increment_version = any(field in update_fields for field in important_fields)
        else:
            # If update_fields is None, increment to be safe
            should_increment_version = True
        
        if should_increment_version:
            # Update global strategy config version (not account-specific)
            update_strategy_config_version_in_redis(instance.id)
            logger.info(f"Incremented global strategy config version for strategy {instance.id}")
            
    except Exception as e:
        logger.error(f"Failed to update Redis for strategy {instance.id}: {e}")

