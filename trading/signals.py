from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import SubscriptionPayment, UserTradeAccount, PaymentStatus, SubscriptionStatus, BotStrategy
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=SubscriptionPayment)
def handle_payment_status_change(sender, instance, **kwargs):
    """
    Handle payment status changes and update trade account accordingly
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
        
        # Get the associated trade account
        trade_account = instance.trade_account
        
        # Handle COMPLETED status
        if new_status == PaymentStatus.COMPLETED and old_status != PaymentStatus.COMPLETED:
            # Activate the account
            trade_account.subscription_status = SubscriptionStatus.ACTIVE
            
            # Check if this is a renewal by checking admin_notes
            is_renewal = instance.admin_notes and 'Renewal for account:' in instance.admin_notes
            
            if is_renewal:
                # For renewal, extend from current expiry or start fresh
                current_expiry = trade_account.subscription_expiry
                if current_expiry and current_expiry > timezone.now():
                    # Still active, extend from current expiry
                    trade_account.subscription_expiry = current_expiry + timedelta(days=instance.subscription_package.duration_days)
                else:
                    # Expired or no expiry, start fresh
                    trade_account.subscription_start = timezone.now()
                    trade_account.subscription_expiry = timezone.now() + timedelta(days=instance.subscription_package.duration_days)
            else:
                # New subscription
                # Set subscription dates
                if not trade_account.subscription_start or trade_account.subscription_status == SubscriptionStatus.PENDING:
                    trade_account.subscription_start = timezone.now()
                
                # Calculate expiry date based on package duration
                trade_account.subscription_expiry = timezone.now() + timedelta(days=instance.subscription_package.duration_days)
            
            # Update package if changed (optional, for package upgrades)
            if trade_account.subscription_package != instance.subscription_package:
                trade_account.subscription_package = instance.subscription_package
            
            # Set verified timestamp
            instance.verified_at = timezone.now()
            
            trade_account.save(update_fields=['subscription_status', 'subscription_start', 'subscription_expiry', 'subscription_package', 'updated_at'])
            
        # Handle FAILED status - keep account in PENDING, allow re-upload
        elif new_status == PaymentStatus.FAILED:
            # Keep account status as PENDING so user can upload new slip
            if trade_account.subscription_status == SubscriptionStatus.PENDING:
                pass  # No change needed, stays PENDING
            
        # Handle REFUNDED status
        elif new_status == PaymentStatus.REFUNDED:
            # Cancel the subscription
            trade_account.subscription_status = SubscriptionStatus.CANCELLED
            trade_account.save(update_fields=['subscription_status', 'updated_at'])
            
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

