from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from decimal import Decimal, InvalidOperation
from trading.models import TradeTransaction, UserTradeAccount
from .authentication import require_bot_api_key
import json


@require_http_methods(["POST"])
@require_bot_api_key
def create_update_order(request):
    """
    Create or update order position for any MT5 account.
    Bot sends mt5_account_id to identify which account the order belongs to.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        }, status=400)
    
    # Validate required fields
    required_fields = [
        'mt5_account_id', 'mt5_order_id', 'symbol',
        'position_type', 'position_status', 'opened_at',
        'entry_price', 'lot_size'
    ]
    
    errors = {}
    for field in required_fields:
        if field not in data:
            errors[field] = ['This field is required']
    
    if errors:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid data',
            'errors': errors
        }, status=400)
    
    # Find the trade account by MT5 account ID
    try:
        trade_account = UserTradeAccount.objects.get(
            mt5_account_id=str(data['mt5_account_id']),
            is_active=True
        )
    except UserTradeAccount.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': f"Trade account {data['mt5_account_id']} not found"
        }, status=404)
    
    # Parse datetime fields
    try:
        opened_at = parse_datetime(data['opened_at'])
        if not opened_at:
            raise ValueError("Invalid datetime format")
        closed_at = parse_datetime(data.get('closed_at')) if data.get('closed_at') else None
    except (ValueError, TypeError):
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid datetime format. Use ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ'
        }, status=400)
    
    # Convert decimal fields
    try:
        decimal_fields = {
            'entry_price': Decimal(str(data['entry_price'])),
            'lot_size': Decimal(str(data['lot_size'])),
            'profit_loss': Decimal(str(data.get('profit_loss', 0))),
            'commission': Decimal(str(data.get('commission', 0))),
            'swap_fee': Decimal(str(data.get('swap_fee', 0))),
        }
        
        if data.get('exit_price'):
            decimal_fields['exit_price'] = Decimal(str(data['exit_price']))
        if data.get('take_profit'):
            decimal_fields['take_profit'] = Decimal(str(data['take_profit']))
        if data.get('stop_loss'):
            decimal_fields['stop_loss'] = Decimal(str(data['stop_loss']))
        if data.get('account_balance_at_close'):
            decimal_fields['account_balance_at_close'] = Decimal(str(data['account_balance_at_close']))
            
    except (ValueError, InvalidOperation):
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid decimal format in price/amount fields'
        }, status=400)
    
    # Validate position type and status
    if data['position_type'] not in ['BUY', 'SELL']:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid position_type. Must be BUY or SELL'
        }, status=400)
    
    if data['position_status'] not in ['OPEN', 'CLOSED', 'PENDING']:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid position_status. Must be OPEN, CLOSED, or PENDING'
        }, status=400)
    
    # Get or create transaction
    transaction, created = TradeTransaction.objects.get_or_create(
        trade_account=trade_account,
        mt5_order_id=data['mt5_order_id'],
        defaults={
            'symbol': data['symbol'],
            'position_type': data['position_type'],
            'position_status': data['position_status'],
            'opened_at': opened_at,
            'closed_at': closed_at,
            **decimal_fields
        }
    )
    
    # If updating existing transaction
    if not created:
        transaction.position_status = data['position_status']
        transaction.closed_at = closed_at
        transaction.exit_price = decimal_fields.get('exit_price')
        transaction.profit_loss = decimal_fields['profit_loss']
        transaction.commission = decimal_fields['commission']
        transaction.swap_fee = decimal_fields['swap_fee']
        transaction.account_balance_at_close = decimal_fields.get('account_balance_at_close')
        transaction.save()
    
    # Update account balance if provided
    if data.get('current_balance'):
        try:
            trade_account.current_balance = Decimal(str(data['current_balance']))
        except (ValueError, InvalidOperation):
            pass
    
    # Update last sync time
    trade_account.last_sync_datetime = timezone.now()
    trade_account.save(update_fields=['last_sync_datetime', 'current_balance'])
    
    return JsonResponse({
        'status': 'success',
        'message': 'Order created successfully' if created else 'Order updated successfully',
        'order_id': data['mt5_order_id'],
        'action': 'created' if created else 'updated',
        'account_id': str(trade_account.mt5_account_id)
    }, status=201 if created else 200)


@require_http_methods(["GET"])
@require_bot_api_key
def get_account_config(request, mt5_account_id):
    """
    Get account subscription status and trading configuration.
    Bot uses this to check if account is active and get trading settings.
    """
    try:
        trade_account = UserTradeAccount.objects.get(
            mt5_account_id=str(mt5_account_id),
            is_active=True
        )
    except UserTradeAccount.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': f"Trade account {mt5_account_id} not found"
        }, status=404)
    
    # Calculate days remaining
    days_remaining = 0
    if trade_account.subscription_expiry:
        delta = trade_account.subscription_expiry - timezone.now()
        days_remaining = max(0, delta.days)
    
    return JsonResponse({
        'status': 'success',
        'data': {
            'account_id': trade_account.mt5_account_id,
            'account_name': trade_account.account_name,
            'broker_name': trade_account.broker_name,
            'broker_server': trade_account.mt5_server,
            'bot_status': trade_account.bot_status,
            'subscription_status': trade_account.subscription_status,
            'subscription_expiry': trade_account.subscription_expiry.isoformat() if trade_account.subscription_expiry else None,
            'days_remaining': days_remaining,
            'trade_config': trade_account.trade_config or {},
            'current_balance': str(trade_account.current_balance),
            'last_sync': trade_account.last_sync_datetime.isoformat() if trade_account.last_sync_datetime else None
        }
    }, status=200)


@require_http_methods(["POST"])
@require_bot_api_key
def bot_heartbeat(request):
    """
    Receive bot heartbeat ping to indicate bot is still running.
    Bot should call this endpoint regularly (e.g., every 60 seconds).
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        }, status=400)
    
    # Validate required fields
    if 'mt5_account_id' not in data:
        return JsonResponse({
            'status': 'error',
            'message': 'mt5_account_id is required'
        }, status=400)
    
    # Find the trade account
    try:
        trade_account = UserTradeAccount.objects.get(
            mt5_account_id=str(data['mt5_account_id']),
            is_active=True
        )
    except UserTradeAccount.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': f"Trade account {data['mt5_account_id']} not found"
        }, status=404)
    
    # Update bot status if provided
    if 'bot_status' in data:
        if data['bot_status'] in ['ACTIVE', 'PAUSED', 'DOWN']:
            trade_account.bot_status = data['bot_status']
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid bot_status. Must be ACTIVE, PAUSED, or DOWN'
            }, status=400)
    
    # Update balance if provided
    if 'current_balance' in data:
        try:
            trade_account.current_balance = Decimal(str(data['current_balance']))
        except (ValueError, InvalidOperation):
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid current_balance format'
            }, status=400)
    
    # Update last sync time
    trade_account.last_sync_datetime = timezone.now()
    trade_account.save(update_fields=['bot_status', 'current_balance', 'last_sync_datetime'])
    
    # Check if bot should continue (subscription active)
    should_continue = (
        trade_account.subscription_status == 'ACTIVE' and 
        trade_account.subscription_expiry and
        trade_account.subscription_expiry > timezone.now()
    )
    
    return JsonResponse({
        'status': 'success',
        'message': 'Heartbeat received',
        'server_time': timezone.now().isoformat(),
        'should_continue': should_continue,
        'subscription_status': trade_account.subscription_status,
        'days_remaining': (trade_account.subscription_expiry - timezone.now()).days if trade_account.subscription_expiry else 0
    }, status=200)
