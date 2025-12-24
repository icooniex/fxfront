from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.db import transaction
from django.db.models import Sum, Count, Q
from decimal import Decimal, InvalidOperation
from trading.models import (
    TradeTransaction, 
    UserTradeAccount, 
    BotStrategy, 
    BacktestResult
)
from .authentication import require_bot_api_key
import json
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)


def get_bot_strategy_from_comment(comment, trade_account):
    """
    Parse comment field to extract bot strategy ID and find the BotStrategy instance.
    Comment format: ID_StrategyName_Symbol (e.g., 5_MeanReversion_EURUSD)
    
    Returns:
        BotStrategy instance or falls back to active_bot if not found
    """
    if not comment:
        return trade_account.active_bot
    
    try:
        # Split by underscore and take the first part as bot_strategy_id
        parts = comment.split('_')
        if not parts or len(parts) < 1:
            return trade_account.active_bot
        
        bot_strategy_id = parts[0]
        
        # Try to convert to integer and find BotStrategy by ID
        try:
            bot_strategy_id = int(bot_strategy_id)
            bot_strategy = BotStrategy.objects.get(
                id=bot_strategy_id,
                is_active=True
            )
            return bot_strategy
        except (ValueError, BotStrategy.DoesNotExist):
            # If ID is invalid or bot not found, fallback to active_bot
            logger.warning(f"Bot strategy ID '{bot_strategy_id}' from comment '{comment}' not found")
            return trade_account.active_bot
        
    except Exception as e:
        logger.warning(f"Error parsing comment '{comment}': {e}")
        return trade_account.active_bot


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
    
    # Validate required fields (always required)
    required_fields = ['mt5_account_id', 'mt5_order_id']
    
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
    
    # Check if this is an update (order already exists)
    try:
        existing_transaction = TradeTransaction.objects.get(
            trade_account=trade_account,
            mt5_order_id=data['mt5_order_id']
        )
        is_update = True
    except TradeTransaction.DoesNotExist:
        is_update = False
        # For new orders, these fields are required
        create_required_fields = ['symbol', 'position_type', 'opened_at', 'entry_price', 'lot_size']
        for field in create_required_fields:
            if field not in data:
                errors[field] = ['This field is required for creating new orders']
        
        if errors:
            return JsonResponse({
                'status': 'error',
                'message': 'Missing required fields for creating new order',
                'errors': errors
            }, status=400)
    
    # Parse datetime fields
    opened_at = None
    if data.get('opened_at'):
        try:
            opened_at = parse_datetime(data['opened_at'])
            if not opened_at:
                raise ValueError("Invalid datetime format")
        except (ValueError, TypeError):
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid opened_at datetime format. Use ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ'
            }, status=400)
    
    closed_at = None
    if data.get('closed_at'):
        try:
            closed_at = parse_datetime(data['closed_at'])
        except (ValueError, TypeError):
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid closed_at datetime format. Use ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ'
            }, status=400)
    
    # Convert decimal fields (only if provided)
    decimal_fields = {}
    try:
        if data.get('entry_price'):
            decimal_fields['entry_price'] = Decimal(str(data['entry_price']))
        if data.get('lot_size'):
            decimal_fields['lot_size'] = Decimal(str(data['lot_size']))
        if data.get('profit_loss') is not None:
            decimal_fields['profit_loss'] = Decimal(str(data['profit_loss']))
        if data.get('commission') is not None:
            decimal_fields['commission'] = Decimal(str(data['commission']))
        if data.get('swap_fee') is not None:
            decimal_fields['swap_fee'] = Decimal(str(data['swap_fee']))
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
    
    # Validate position type if provided
    if data.get('position_type') and data['position_type'] not in ['BUY', 'SELL']:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid position_type. Must be BUY or SELL'
        }, status=400)
    
    # Validate position status if provided
    if data.get('position_status') and data['position_status'] not in ['OPEN', 'CLOSED', 'PENDING']:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid position_status. Must be OPEN, CLOSED, or PENDING'
        }, status=400)
    
    # Validate close_reason if provided
    if data.get('close_reason') and data['close_reason'] not in ['MANUAL', 'TP', 'SL', 'MARGIN_CALL']:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid close_reason. Must be MANUAL, TP, SL, or MARGIN_CALL'
        }, status=400)
    
    # Create or update transaction
    if is_update:
        # Update existing transaction
        transaction = existing_transaction
        
        if data.get('position_status'):
            transaction.position_status = data['position_status']
        if closed_at is not None:
            transaction.closed_at = closed_at
        if data.get('close_reason'):
            transaction.close_reason = data['close_reason']
        
        # Update decimal fields if provided
        if 'exit_price' in decimal_fields:
            transaction.exit_price = decimal_fields['exit_price']
        if 'take_profit' in decimal_fields:
            transaction.take_profit = decimal_fields['take_profit']
        if 'stop_loss' in decimal_fields:
            transaction.stop_loss = decimal_fields['stop_loss']
        if 'profit_loss' in decimal_fields:
            transaction.profit_loss = decimal_fields['profit_loss']
        if 'commission' in decimal_fields:
            transaction.commission = decimal_fields['commission']
        if 'swap_fee' in decimal_fields:
            transaction.swap_fee = decimal_fields['swap_fee']
        if 'account_balance_at_close' in decimal_fields:
            transaction.account_balance_at_close = decimal_fields['account_balance_at_close']
        
        transaction.save()
        created = False
    else:
        # Get bot strategy from comment field
        bot_strategy = get_bot_strategy_from_comment(data.get('comment'), trade_account)
        
        # Create new transaction
        transaction = TradeTransaction.objects.create(
            trade_account=trade_account,
            bot_strategy=bot_strategy,
            mt5_order_id=data['mt5_order_id'],
            symbol=data['symbol'],
            position_type=data['position_type'],
            position_status=data.get('position_status', 'OPEN'),
            opened_at=opened_at,
            closed_at=closed_at,
            close_reason=data.get('close_reason'),
            entry_price=decimal_fields['entry_price'],
            lot_size=decimal_fields['lot_size'],
            exit_price=decimal_fields.get('exit_price'),
            take_profit=decimal_fields.get('take_profit'),
            stop_loss=decimal_fields.get('stop_loss'),
            profit_loss=decimal_fields.get('profit_loss', Decimal('0.0000')),
            commission=decimal_fields.get('commission', Decimal('0.0000')),
            swap_fee=decimal_fields.get('swap_fee', Decimal('0.0000')),
            account_balance_at_close=decimal_fields.get('account_balance_at_close')
        )
        created = True
    
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


@require_http_methods(["POST"])
@require_bot_api_key
def batch_create_update_orders(request):
    """
    Batch create or update multiple orders in a single request.
    Much faster than calling create_update_order multiple times.
    
    Limits: Max 500 orders per batch to prevent timeout.
    
    Expected JSON format - Just an array of orders:
    [
        {
            "mt5_account_id": "12345",
            "mt5_order_id": 123,
            "symbol": "EURUSD",
            "position_type": "BUY",
            "current_balance": 10000.00,
            ...
        },
        ...
    ]
    """
    try:
        orders_data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        }, status=400)
    
    # Validate that it's an array
    if not isinstance(orders_data, list):
        return JsonResponse({
            'status': 'error',
            'message': 'Request body must be an array of orders'
        }, status=400)
    
    if len(orders_data) == 0:
        return JsonResponse({
            'status': 'error',
            'message': 'Orders array cannot be empty'
        }, status=400)
    
    # Limit batch size to prevent timeout
    if len(orders_data) > 500:
        return JsonResponse({
            'status': 'error',
            'message': 'Batch size limit exceeded. Maximum 500 orders per request.'
        }, status=400)
    
    # Process orders
    results = {
        'created': [],
        'updated': [],
        'failed': []
    }
    
    # Pre-fetch all accounts and existing orders to minimize DB queries
    account_ids = list(set(str(order.get('mt5_account_id')) for order in orders_data if order.get('mt5_account_id')))
    accounts_cache = {}
    
    if account_ids:
        accounts = UserTradeAccount.objects.filter(
            mt5_account_id__in=account_ids,
            is_active=True
        ).select_related('active_bot')
        accounts_cache = {str(acc.mt5_account_id): acc for acc in accounts}
    
    # Pre-fetch existing orders
    order_ids_by_account = {}
    for order_data in orders_data:
        acc_id = str(order_data.get('mt5_account_id', ''))
        if acc_id in accounts_cache:
            if acc_id not in order_ids_by_account:
                order_ids_by_account[acc_id] = []
            if 'mt5_order_id' in order_data:
                order_ids_by_account[acc_id].append(order_data['mt5_order_id'])
    
    existing_orders_cache = {}
    for acc_id, order_ids in order_ids_by_account.items():
        if order_ids:
            account = accounts_cache[acc_id]
            existing = TradeTransaction.objects.filter(
                trade_account=account,
                mt5_order_id__in=order_ids
            )
            for order in existing:
                key = f"{acc_id}_{order.mt5_order_id}"
                existing_orders_cache[key] = order
    
    for idx, order_data in enumerate(orders_data):
        try:
            # Validate required fields
            if 'mt5_account_id' not in order_data:
                results['failed'].append({
                    'index': idx,
                    'order_id': order_data.get('mt5_order_id'),
                    'error': 'mt5_account_id is required'
                })
                continue
            
            if 'mt5_order_id' not in order_data:
                results['failed'].append({
                    'index': idx,
                    'order_id': None,
                    'error': 'mt5_order_id is required'
                })
                continue
            
            mt5_account_id = str(order_data['mt5_account_id'])
            mt5_order_id = order_data['mt5_order_id']
            
            # Get trade account from cache
            if mt5_account_id not in accounts_cache:
                results['failed'].append({
                    'index': idx,
                    'order_id': mt5_order_id,
                    'error': f"Trade account {mt5_account_id} not found"
                })
                continue
            
            trade_account = accounts_cache[mt5_account_id]
            
            # Check if order exists in cache
            cache_key = f"{mt5_account_id}_{mt5_order_id}"
            existing_transaction = existing_orders_cache.get(cache_key)
            is_update = existing_transaction is not None
            
            if not is_update:
                # Validate required fields for new orders
                required_fields = ['symbol', 'position_type', 'opened_at', 'entry_price', 'lot_size']
                missing_fields = [f for f in required_fields if f not in order_data]
                
                if missing_fields:
                    results['failed'].append({
                        'index': idx,
                        'order_id': mt5_order_id,
                        'error': f"Missing required fields: {', '.join(missing_fields)}"
                    })
                    continue
            
            # Parse datetime fields
            opened_at = None
            if order_data.get('opened_at'):
                try:
                    opened_at = parse_datetime(order_data['opened_at'])
                    if not opened_at:
                        raise ValueError("Invalid datetime format")
                except (ValueError, TypeError):
                    results['failed'].append({
                        'index': idx,
                        'order_id': mt5_order_id,
                        'error': 'Invalid opened_at datetime format'
                    })
                    continue
            
            closed_at = None
            if order_data.get('closed_at'):
                try:
                    closed_at = parse_datetime(order_data['closed_at'])
                except (ValueError, TypeError):
                    results['failed'].append({
                        'index': idx,
                        'order_id': mt5_order_id,
                        'error': 'Invalid closed_at datetime format'
                    })
                    continue
            
            # Convert decimal fields
            decimal_fields = {}
            try:
                if order_data.get('entry_price'):
                    decimal_fields['entry_price'] = Decimal(str(order_data['entry_price']))
                if order_data.get('lot_size'):
                    decimal_fields['lot_size'] = Decimal(str(order_data['lot_size']))
                if order_data.get('profit_loss') is not None:
                    decimal_fields['profit_loss'] = Decimal(str(order_data['profit_loss']))
                if order_data.get('commission') is not None:
                    decimal_fields['commission'] = Decimal(str(order_data['commission']))
                if order_data.get('swap_fee') is not None:
                    decimal_fields['swap_fee'] = Decimal(str(order_data['swap_fee']))
                if order_data.get('exit_price'):
                    decimal_fields['exit_price'] = Decimal(str(order_data['exit_price']))
                if order_data.get('take_profit'):
                    decimal_fields['take_profit'] = Decimal(str(order_data['take_profit']))
                if order_data.get('stop_loss'):
                    decimal_fields['stop_loss'] = Decimal(str(order_data['stop_loss']))
                if order_data.get('account_balance_at_close'):
                    decimal_fields['account_balance_at_close'] = Decimal(str(order_data['account_balance_at_close']))
            except (ValueError, InvalidOperation):
                results['failed'].append({
                    'index': idx,
                    'order_id': mt5_order_id,
                    'error': 'Invalid decimal format in price/amount fields'
                })
                continue
            
            # Validate enums
            if order_data.get('position_type') and order_data['position_type'] not in ['BUY', 'SELL']:
                results['failed'].append({
                    'index': idx,
                    'order_id': mt5_order_id,
                    'error': 'Invalid position_type. Must be BUY or SELL'
                })
                continue
            
            if order_data.get('position_status') and order_data['position_status'] not in ['OPEN', 'CLOSED', 'PENDING']:
                results['failed'].append({
                    'index': idx,
                    'order_id': mt5_order_id,
                    'error': 'Invalid position_status'
                })
                continue
            
            if order_data.get('close_reason') and order_data['close_reason'] not in ['MANUAL', 'TP', 'SL', 'MARGIN_CALL', 'Mobile', 'Web', 'Expert']:
                results['failed'].append({
                    'index': idx,
                    'order_id': mt5_order_id,
                    'error': 'Invalid close_reason'
                })
                continue
            
            # Create or update within transaction
            with transaction.atomic():
                if is_update:
                    # Update existing transaction
                    trans = existing_transaction
                    
                    if order_data.get('position_status'):
                        trans.position_status = order_data['position_status']
                    if closed_at is not None:
                        trans.closed_at = closed_at
                    if order_data.get('close_reason'):
                        trans.close_reason = order_data['close_reason']
                    
                    # Update decimal fields if provided
                    for field, value in decimal_fields.items():
                        setattr(trans, field, value)
                    
                    trans.save()
                    results['updated'].append(mt5_order_id)
                else:
                    # Get bot strategy from comment field
                    bot_strategy = get_bot_strategy_from_comment(order_data.get('comment'), trade_account)
                    
                    # Create new transaction
                    TradeTransaction.objects.create(
                        trade_account=trade_account,
                        bot_strategy=bot_strategy,
                        mt5_order_id=mt5_order_id,
                        symbol=order_data['symbol'],
                        position_type=order_data['position_type'],
                        position_status=order_data.get('position_status', 'OPEN'),
                        opened_at=opened_at,
                        closed_at=closed_at,
                        close_reason=order_data.get('close_reason'),
                        entry_price=decimal_fields['entry_price'],
                        lot_size=decimal_fields['lot_size'],
                        exit_price=decimal_fields.get('exit_price'),
                        take_profit=decimal_fields.get('take_profit'),
                        stop_loss=decimal_fields.get('stop_loss'),
                        profit_loss=decimal_fields.get('profit_loss', Decimal('0.0000')),
                        commission=decimal_fields.get('commission', Decimal('0.0000')),
                        swap_fee=decimal_fields.get('swap_fee', Decimal('0.0000')),
                        account_balance_at_close=decimal_fields.get('account_balance_at_close')
                    )
                    results['created'].append(mt5_order_id)
                
                # Update account balance if provided in this order
                if order_data.get('current_balance'):
                    try:
                        trade_account.current_balance = Decimal(str(order_data['current_balance']))
                        trade_account.last_sync_datetime = timezone.now()
                        trade_account.save(update_fields=['last_sync_datetime', 'current_balance'])
                    except (ValueError, InvalidOperation):
                        pass
                    
        except Exception as e:
            results['failed'].append({
                'index': idx,
                'order_id': order_data.get('mt5_order_id'),
                'error': str(e)
            })
    
    # Limit response size - only return failed order details
    response_data = {
        'status': 'success',
        'message': f"Processed {len(orders_data)} orders",
        'results': {
            'created': len(results['created']),
            'updated': len(results['updated']),
            'failed': len(results['failed'])
        }
    }
    
    # Only include failed orders if there are any (and not too many)
    if results['failed'] and len(results['failed']) <= 50:
        response_data['results']['failed_orders'] = results['failed']
    elif results['failed']:
        response_data['results']['failed_count'] = len(results['failed'])
        response_data['results']['note'] = 'Too many failures to list. Check server logs.'
    
    return JsonResponse(response_data, status=200)


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
    
    Also returns trade configuration and strategy parameters in the response,
    so bot can update its settings without making additional API calls.
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
    
    # Find the trade account with strategy info
    try:
        trade_account = UserTradeAccount.objects.select_related('active_bot').get(
            mt5_account_id=str(data['mt5_account_id']),
            is_active=True
        )
    except UserTradeAccount.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': f"Trade account {data['mt5_account_id']} not found"
        }, status=404)
    
    # Update bot status if provided
    if 'bot_status' in data and data['bot_status'] is not None:
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
            new_balance = Decimal(str(data['current_balance']))
            trade_account.current_balance = new_balance
            
            # Update peak balance if current balance exceeds it
            if new_balance > trade_account.peak_balance:
                trade_account.peak_balance = new_balance
                
        except (ValueError, InvalidOperation):
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid current_balance format'
            }, status=400)
    
    # Update last sync time
    trade_account.last_sync_datetime = timezone.now()
    trade_account.save(update_fields=['bot_status', 'current_balance', 'peak_balance', 'last_sync_datetime'])
    
    # Check if bot should continue (subscription active)
    should_continue = (
        trade_account.subscription_status == 'ACTIVE' and 
        trade_account.subscription_expiry and
        trade_account.subscription_expiry > timezone.now()
    )
    
    # Get trade config and strategy parameters
    trade_config = trade_account.trade_config or {}
    strategy_info = None
    
    # Build risk management configuration
    risk_config = {}
    
    # Add news filter if enabled
    if trade_config.get('auto_pause_on_news'):
        risk_config['auto_pause_on_news'] = True
    
    # Add drawdown protection if configured
    if trade_config.get('daily_dd_limit'):
        risk_config['daily_dd_limit'] = trade_config.get('daily_dd_limit')
    
    if trade_config.get('max_dd_limit'):
        risk_config['max_dd_limit'] = trade_config.get('max_dd_limit')
    
    # Add dynamic position sizing if enabled
    if trade_config.get('dynamic_position_sizing_enabled'):
        risk_config['dynamic_position_sizing'] = {
            'enabled': True,
            'risk_percentage_per_trade': trade_config.get('risk_percentage_per_trade', 0.5)
        }
    else:
        risk_config['dynamic_position_sizing'] = {
            'enabled': False
        }
    
    if trade_account.active_bot:
        # Get current_parameters which should be organized by symbol
        # Format: {"EURUSD": {...params...}, "GBPUSD": {...params...}}
        # For pair trading: {"EURUSD/GBPUSD": {...params...}}
        current_parameters = trade_account.active_bot.current_parameters or {}
        
        strategy_info = {
            'id': trade_account.active_bot.id,
            'name': trade_account.active_bot.name,
            'version': trade_account.active_bot.version,
            'strategy_type': trade_account.active_bot.strategy_type,
            'bot_strategy_class': trade_account.active_bot.bot_strategy_class,
            'status': trade_account.active_bot.status,
            'is_pair_trading': trade_account.active_bot.is_pair_trading,
            'allowed_symbols': trade_account.active_bot.allowed_symbols,
            'parameters_by_symbol': current_parameters,
        }
    
    return JsonResponse({
        'status': 'success',
        'message': 'Heartbeat received',
        'server_time': timezone.now().isoformat(),
        'should_continue': should_continue,
        'bot_status': trade_account.bot_status,
        'subscription_status': trade_account.subscription_status,
        'days_remaining': (trade_account.subscription_expiry - timezone.now()).days if trade_account.subscription_expiry else 0,
        'current_balance': str(trade_account.current_balance),
        'peak_balance': str(trade_account.peak_balance),
        'trade_config': trade_config,
        'risk_config': risk_config,
        'strategy': strategy_info,
    }, status=200)


@require_http_methods(["GET"])
@login_required
def get_account_live_data(request, account_id):
    """
    Get real-time account data for frontend updates.
    Returns account balance, stats, open positions, and recent closed positions.
    """
    try:
        # Get account and verify ownership
        account = UserTradeAccount.objects.get(
            id=account_id,
            user=request.user,
            is_active=True
        )
    except UserTradeAccount.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Account not found'
        }, status=404)
    
    # Get open positions
    open_positions = TradeTransaction.objects.filter(
        trade_account=account,
        position_status='OPEN',
        is_active=True
    ).order_by('-opened_at')
    
    # Get recent closed positions (last 10)
    closed_positions = TradeTransaction.objects.filter(
        trade_account=account,
        position_status='CLOSED',
        is_active=True
    ).order_by('-closed_at')[:10]
    
    # Calculate stats
    all_closed = TradeTransaction.objects.filter(
        trade_account=account,
        position_status='CLOSED',
        is_active=True
    )
    
    total_trades = all_closed.count()
    closed_pnl = sum(t.profit_loss for t in all_closed)
    winning_trades = all_closed.filter(profit_loss__gt=0).count()
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    # Calculate current P&L from open positions
    current_open_pnl = sum(pos.profit_loss for pos in open_positions)
    
    # Total P&L = Closed P&L + Current Open P&L
    total_pnl = closed_pnl + current_open_pnl
    
    # Format open positions
    open_positions_data = []
    for pos in open_positions:
        open_positions_data.append({
            'id': pos.id,
            'mt5_order_id': pos.mt5_order_id,
            'symbol': pos.symbol,
            'position_type': pos.position_type,
            'position_type_display': pos.get_position_type_display(),
            'entry_price': str(pos.entry_price),
            'lot_size': str(pos.lot_size),
            'take_profit': str(pos.take_profit) if pos.take_profit else None,
            'stop_loss': str(pos.stop_loss) if pos.stop_loss else None,
            'profit_loss': float(pos.profit_loss),
            'opened_at': pos.opened_at.strftime('%d %b %y %H:%M'),
        })
    
    # Format closed positions
    closed_positions_data = []
    for pos in closed_positions:
        closed_positions_data.append({
            'id': pos.id,
            'mt5_order_id': pos.mt5_order_id,
            'symbol': pos.symbol,
            'position_type': pos.position_type,
            'position_type_display': pos.get_position_type_display(),
            'close_reason': pos.close_reason,
            'close_reason_display': pos.get_close_reason_display() if pos.close_reason else None,
            'entry_price': str(pos.entry_price),
            'lot_size': str(pos.lot_size),
            'profit_loss': float(pos.profit_loss),
            'closed_at': pos.closed_at.strftime('%d %b %y %H:%M') if pos.closed_at else None,
        })
    
    return JsonResponse({
        'status': 'success',
        'data': {
            'account': {
                'balance': float(account.current_balance),
                'bot_status': account.bot_status,
                'bot_status_display': account.get_bot_status_display(),
            },
            'stats': {
                'total_pnl': float(total_pnl),
                'total_trades': total_trades,
                'win_rate': round(win_rate, 1),
            },
            'open_positions': open_positions_data,
            'closed_positions': closed_positions_data,
        },
        'timestamp': timezone.now().isoformat()
    })


@require_http_methods(["GET"])
@login_required
def get_dashboard_live_data(request):
    """
    Get real-time dashboard data for all user accounts.
    Returns summary data for each trading account.
    """
    # Get all active accounts for user
    accounts = UserTradeAccount.objects.filter(
        user=request.user,
        is_active=True
    ).order_by('-created_at')
    
    accounts_data = []
    for account in accounts:
        # Get open positions count and current P&L
        open_positions = TradeTransaction.objects.filter(
            trade_account=account,
            position_status='OPEN',
            is_active=True
        )
        
        open_count = open_positions.count()
        current_pnl = sum(pos.profit_loss for pos in open_positions)
        
        # Get total stats
        all_closed = TradeTransaction.objects.filter(
            trade_account=account,
            position_status='CLOSED',
            is_active=True
        )
        
        total_trades = all_closed.count()
        closed_pnl = sum(t.profit_loss for t in all_closed)
        
        # Total P&L = Closed P&L + Current Open P&L
        total_pnl = closed_pnl + current_pnl
        
        # Calculate days until expiry
        days_until_expiry = 0
        if account.subscription_expiry:
            delta = account.subscription_expiry - timezone.now()
            days_until_expiry = max(0, delta.days)
        
        accounts_data.append({
            'id': account.id,
            'account_name': account.account_name,
            'broker_name': account.broker_name,
            'balance': float(account.current_balance),
            'bot_status': account.bot_status,
            'bot_status_display': account.get_bot_status_display(),
            'open_positions_count': open_count,
            'current_pnl': float(current_pnl),
            'total_pnl': float(total_pnl),
            'total_trades': total_trades,
            'days_until_expiry': days_until_expiry,
        })
    
    return JsonResponse({
        'status': 'success',
        'data': {
            'accounts': accounts_data,
        },
        'timestamp': timezone.now().isoformat()
    })


@require_http_methods(["GET"])
@login_required
def get_account_open_positions_only(request, account_id):
    """
    OPTIMIZED: Get ONLY open positions for live updates.
    This is much faster than get_account_live_data.
    Use this for frequent polling (every 1 second).
    """
    try:
        account = UserTradeAccount.objects.get(
            id=account_id,
            user=request.user,
            is_active=True
        )
    except UserTradeAccount.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Account not found'
        }, status=404)
    
    # Use aggregation for fast stats
    open_stats = TradeTransaction.objects.filter(
        trade_account=account,
        position_status='OPEN',
        is_active=True
    ).aggregate(
        open_count=Count('id'),
        current_open_pnl=Sum('profit_loss')
    )
    
    # Get closed P&L for total calculation
    closed_stats = TradeTransaction.objects.filter(
        trade_account=account,
        position_status='CLOSED',
        is_active=True
    ).aggregate(
        closed_pnl=Sum('profit_loss')
    )
    
    current_open_pnl = open_stats['current_open_pnl'] or Decimal('0')
    closed_pnl = closed_stats['closed_pnl'] or Decimal('0')
    total_pnl = closed_pnl + current_open_pnl
    
    # Get open positions with only essential fields
    open_positions = TradeTransaction.objects.filter(
        trade_account=account,
        position_status='OPEN',
        is_active=True
    ).only(
        'id', 'mt5_order_id', 'symbol', 'position_type',
        'profit_loss', 'updated_at'
    ).order_by('-opened_at')[:100]  # Limit to 100 most recent
    
    positions_data = [{
        'id': pos.id,
        'mt5_order_id': pos.mt5_order_id,
        'symbol': pos.symbol,
        'position_type': pos.position_type,
        'profit_loss': float(pos.profit_loss),
        'updated_at': pos.updated_at.isoformat(),
    } for pos in open_positions]
    
    return JsonResponse({
        'status': 'success',
        'data': {
            'balance': float(account.current_balance),
            'open_count': open_stats['open_count'] or 0,
            'current_open_pnl': float(current_open_pnl),
            'total_pnl': float(total_pnl),
            'open_positions': positions_data,
        },
        'timestamp': timezone.now().isoformat()
    })


@require_http_methods(["GET"])
@login_required
def get_account_closed_positions(request, account_id):
    """
    Get closed positions history.
    Call this only when needed (not in polling loop).
    """
    try:
        account = UserTradeAccount.objects.get(
            id=account_id,
            user=request.user,
            is_active=True
        )
    except UserTradeAccount.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Account not found'
        }, status=404)
    
    # Get pagination params
    limit = int(request.GET.get('limit', 20))
    offset = int(request.GET.get('offset', 0))
    
    # Get closed positions with pagination
    closed_positions = TradeTransaction.objects.filter(
        trade_account=account,
        position_status='CLOSED',
        is_active=True
    ).order_by('-closed_at')[offset:offset+limit]
    
    # Get total count
    total_count = TradeTransaction.objects.filter(
        trade_account=account,
        position_status='CLOSED',
        is_active=True
    ).count()
    
    # Get closed stats using aggregation
    closed_stats = TradeTransaction.objects.filter(
        trade_account=account,
        position_status='CLOSED',
        is_active=True
    ).aggregate(
        total_trades=Count('id'),
        closed_pnl=Sum('profit_loss'),
        winning_trades=Count('id', filter=Q(profit_loss__gt=0))
    )
    
    total_trades = closed_stats['total_trades'] or 0
    closed_pnl = closed_stats['closed_pnl'] or Decimal('0')
    winning_trades = closed_stats['winning_trades'] or 0
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    positions_data = [{
        'id': pos.id,
        'mt5_order_id': pos.mt5_order_id,
        'symbol': pos.symbol,
        'position_type': pos.position_type,
        'position_type_display': pos.get_position_type_display(),
        'close_reason': pos.close_reason,
        'close_reason_display': pos.get_close_reason_display() if pos.close_reason else None,
        'entry_price': str(pos.entry_price),
        'lot_size': str(pos.lot_size),
        'profit_loss': float(pos.profit_loss),
        'closed_at': pos.closed_at.strftime('%d %b %y %H:%M') if pos.closed_at else None,
    } for pos in closed_positions]
    
    return JsonResponse({
        'status': 'success',
        'data': {
            'stats': {
                'closed_pnl': float(closed_pnl),
                'total_trades': total_trades,
                'win_rate': round(win_rate, 1),
            },
            'closed_positions': positions_data,
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
            }
        },
        'timestamp': timezone.now().isoformat()
    })


# ============================================
# Bot Strategy API Endpoints (for external backtest system)
# ============================================

@require_http_methods(["GET"])
@require_bot_api_key
def get_bot_strategies(request):
    """
    Get list of all bot strategies with their configuration.
    External backtest system uses this to know which bots to backtest.
    """
    strategies = BotStrategy.objects.filter(is_active=True).prefetch_related('allowed_packages')
    
    strategies_data = []
    for bot in strategies:
        strategies_data.append({
            'id': bot.id,
            'name': bot.name,
            'description': bot.description,
            'status': bot.status,
            'version': bot.version,
            'strategy_type': bot.strategy_type,
            'bot_strategy_class': bot.bot_strategy_class,
            'is_pair_trading': bot.is_pair_trading,
            'allowed_symbols': bot.allowed_symbols,
            'allowed_packages': [pkg.id for pkg in bot.allowed_packages.all()],
            'optimization_config': bot.optimization_config,
            'current_parameters': bot.current_parameters,
            'backtest_range_days': bot.backtest_range_days,
            'last_backtest_date': bot.last_backtest_date.isoformat() if bot.last_backtest_date else None,
            'last_optimization_date': bot.last_optimization_date.isoformat() if bot.last_optimization_date else None,
        })
    
    return JsonResponse({
        'status': 'success',
        'data': {
            'strategies': strategies_data,
            'count': len(strategies_data)
        },
        'timestamp': timezone.now().isoformat()
    })


@require_http_methods(["POST"])
@require_bot_api_key
def submit_backtest_result(request):
    """
    Submit backtest result from external backtest system.
    Accepts JSON data with metrics and optional images as multipart/form-data.
    
    Expected data:
    - bot_strategy_id (required)
    - backtest_start_date (required, YYYY-MM-DD)
    - backtest_end_date (required, YYYY-MM-DD)
    - total_trades, winning_trades, losing_trades
    - win_rate, total_profit, avg_profit_per_trade
    - best_trade, worst_trade
    - max_drawdown, max_drawdown_percent
    - raw_data (optional, JSON object)
    - equity_curve_image (optional, file upload)
    - comprehensive_analysis_image (optional, file upload)
    - trading_graph_image (optional, file upload)
    - set_as_latest (optional, boolean, default True)
    """
    try:
        # Check if this is multipart form data or JSON
        if request.content_type and 'multipart/form-data' in request.content_type:
            data = request.POST.dict()
            equity_curve_image = request.FILES.get('equity_curve_image')
            comprehensive_analysis_image = request.FILES.get('comprehensive_analysis_image')
            trading_graph_image = request.FILES.get('trading_graph_image')
        else:
            data = json.loads(request.body)
            equity_curve_image = None
            comprehensive_analysis_image = None
            trading_graph_image = None
    except (json.JSONDecodeError, Exception) as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Invalid request data: {str(e)}'
        }, status=400)
    
    # Validate required fields
    required_fields = ['bot_strategy_id', 'backtest_start_date', 'backtest_end_date']
    errors = {}
    
    for field in required_fields:
        if field not in data:
            errors[field] = ['This field is required']
    
    if errors:
        return JsonResponse({
            'status': 'error',
            'message': 'Missing required fields',
            'errors': errors
        }, status=400)
    
    # Get bot strategy
    try:
        bot_strategy = BotStrategy.objects.get(id=data['bot_strategy_id'], is_active=True)
    except BotStrategy.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': f"Bot strategy {data['bot_strategy_id']} not found"
        }, status=404)
    except ValueError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid bot_strategy_id format'
        }, status=400)
    
    # Parse dates
    try:
        backtest_start_date = datetime.strptime(data['backtest_start_date'], '%Y-%m-%d').date()
        backtest_end_date = datetime.strptime(data['backtest_end_date'], '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid date format. Use YYYY-MM-DD'
        }, status=400)
    
    # Parse numeric fields with defaults
    try:
        total_trades = int(data.get('total_trades', 0))
        winning_trades = int(data.get('winning_trades', 0))
        losing_trades = int(data.get('losing_trades', 0))
        
        win_rate = Decimal(str(data.get('win_rate', '0.00')))
        total_profit = Decimal(str(data.get('total_profit', '0.0000')))
        avg_profit_per_trade = Decimal(str(data.get('avg_profit_per_trade', '0.0000')))
        best_trade = Decimal(str(data.get('best_trade', '0.0000')))
        worst_trade = Decimal(str(data.get('worst_trade', '0.0000')))
        max_drawdown = Decimal(str(data.get('max_drawdown', '0.0000')))
        max_drawdown_percent = Decimal(str(data.get('max_drawdown_percent', '0.00')))
    except (ValueError, InvalidOperation) as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Invalid numeric format: {str(e)}'
        }, status=400)
    
    # Parse raw_data if provided
    raw_data = {}
    if 'raw_data' in data:
        if isinstance(data['raw_data'], str):
            try:
                raw_data = json.loads(data['raw_data'])
            except json.JSONDecodeError:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid raw_data JSON format'
                }, status=400)
        elif isinstance(data['raw_data'], dict):
            raw_data = data['raw_data']
    
    # Determine if this should be set as latest
    set_as_latest = data.get('set_as_latest', 'true').lower() in ['true', '1', 'yes']
    
    # Create backtest result within transaction
    with transaction.atomic():
        # If setting as latest, unset all other latest results for this bot
        if set_as_latest:
            BacktestResult.objects.filter(
                bot_strategy=bot_strategy,
                is_latest=True
            ).update(is_latest=False)
        
        # Create new backtest result
        backtest_result = BacktestResult.objects.create(
            bot_strategy=bot_strategy,
            run_date=timezone.now(),
            backtest_start_date=backtest_start_date,
            backtest_end_date=backtest_end_date,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_profit=total_profit,
            avg_profit_per_trade=avg_profit_per_trade,
            best_trade=best_trade,
            worst_trade=worst_trade,
            max_drawdown=max_drawdown,
            max_drawdown_percent=max_drawdown_percent,
            raw_data=raw_data,
            is_latest=set_as_latest,
            equity_curve_image=equity_curve_image,
            comprehensive_analysis_image=comprehensive_analysis_image,
            trading_graph_image=trading_graph_image
        )
        
        # Update bot strategy's last_backtest_date
        bot_strategy.last_backtest_date = timezone.now()
        bot_strategy.save(update_fields=['last_backtest_date'])
    
    return JsonResponse({
        'status': 'success',
        'message': 'Backtest result submitted successfully',
        'data': {
            'backtest_result_id': backtest_result.id,
            'bot_strategy_id': bot_strategy.id,
            'bot_strategy_name': bot_strategy.name,
            'is_latest': backtest_result.is_latest,
            'run_date': backtest_result.run_date.isoformat()
        }
    }, status=201)


@require_http_methods(["POST"])
@require_bot_api_key
def submit_optimization_result(request):
    """
    Submit optimization result from external optimization system.
    Updates the current_parameters for a bot strategy.
    
    Expected JSON data:
    - bot_strategy_id (required)
    - optimized_parameters (required, JSON object)
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        }, status=400)
    
    # Validate required fields
    if 'bot_strategy_id' not in data:
        return JsonResponse({
            'status': 'error',
            'message': 'bot_strategy_id is required'
        }, status=400)
    
    if 'optimized_parameters' not in data:
        return JsonResponse({
            'status': 'error',
            'message': 'optimized_parameters is required'
        }, status=400)
    
    # Get bot strategy
    try:
        bot_strategy = BotStrategy.objects.get(id=data['bot_strategy_id'], is_active=True)
    except BotStrategy.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': f"Bot strategy {data['bot_strategy_id']} not found"
        }, status=404)
    except ValueError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid bot_strategy_id format'
        }, status=400)
    
    # Validate optimized_parameters is a dict
    optimized_parameters = data['optimized_parameters']
    if not isinstance(optimized_parameters, dict):
        return JsonResponse({
            'status': 'error',
            'message': 'optimized_parameters must be a JSON object'
        }, status=400)
    
    # Update bot strategy's current_parameters and last_optimization_date
    bot_strategy.current_parameters = optimized_parameters
    bot_strategy.last_optimization_date = timezone.now()
    bot_strategy.save(update_fields=['current_parameters', 'last_optimization_date'])
    
    return JsonResponse({
        'status': 'success',
        'message': 'Optimization result submitted successfully',
        'data': {
            'bot_strategy_id': bot_strategy.id,
            'bot_strategy_name': bot_strategy.name,
            'current_parameters': bot_strategy.current_parameters,
            'last_optimization_date': bot_strategy.last_optimization_date.isoformat()
        }
    }, status=200)

