from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import SubscriptionPayment, UserTradeAccount, PaymentStatus, SubscriptionStatus


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
            
            # Set subscription dates
            if not trade_account.subscription_start or trade_account.subscription_status == SubscriptionStatus.PENDING:
                trade_account.subscription_start = timezone.now()
            
            # Calculate expiry date based on package duration
            trade_account.subscription_expiry = timezone.now() + timedelta(days=instance.subscription_package.duration_days)
            
            # Set verified timestamp
            instance.verified_at = timezone.now()
            
            trade_account.save(update_fields=['subscription_status', 'subscription_start', 'subscription_expiry', 'updated_at'])
            
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
