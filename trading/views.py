from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from datetime import timedelta, datetime
from decimal import Decimal, InvalidOperation
import requests
import urllib.parse
import secrets
import logging
from dateutil import parser as date_parser
from .models import (
    UserProfile,
    SubscriptionPackage,
    UserTradeAccount,
    TradeTransaction,
    SubscriptionPayment,
    BotStrategy,
    BacktestResult,
    BotStatus,
    PaymentStatus
)

logger = logging.getLogger(__name__)

# Import Redis client and heartbeat function
try:
    from .api.views import redis_client, update_server_heartbeat_in_redis
except ImportError:
    redis_client = None
    logger.warning("⚠️ Redis client not available")


# ============================================
# Helper Functions
# ============================================

def get_account_data_from_redis(account):
    """
    Get bot status and balance from Redis heartbeat.
    
    Args:
        account: UserTradeAccount instance
        
    Returns:
        dict: {'bot_status': str, 'balance': Decimal}
    """
    if redis_client is None:
        # Fallback to DB data if Redis not available
        return {
            'bot_status': account.bot_status,
            'balance': account.current_balance
        }
    
    try:
        mt5_account_id = str(account.mt5_account_id)
        heartbeat_key = f"bot:heartbeat:{mt5_account_id}"
        
        # Get heartbeat data from Redis
        heartbeat_data = redis_client.hgetall(heartbeat_key)
        
        if not heartbeat_data or 'last_seen' not in heartbeat_data:
            # No heartbeat found, bot is DOWN
            return {
                'bot_status': 'DOWN',
                'balance': account.current_balance
            }
        
        # Get bot_status from Redis
        bot_status = heartbeat_data.get('bot_status') or account.bot_status
        
        # Get balance from Redis
        balance = account.current_balance
        balance_str = heartbeat_data.get('balance') or heartbeat_data.get('current_balance')
        if balance_str:
            try:
                balance = Decimal(str(balance_str))
            except (ValueError, TypeError, InvalidOperation) as e:
                logger.warning(f"Failed to parse balance from Redis: {e}")
        
        return {
            'bot_status': bot_status,
            'balance': balance
        }
    
    except Exception as e:
        logger.error(f"Error getting account data from Redis: {e}")
        # Fallback to DB data on error
        return {
            'bot_status': account.bot_status,
            'balance': account.current_balance
        }


def get_today_high_impact_news():
    """
    Fetch high-impact news for today from FX News API.
    
    Returns:
        list: List of today's high-impact news events
    """
    try:
        # Get API URL from settings
        api_url = settings.FX_NEWS_API_URL
        
        # Fetch news data
        response = requests.get(api_url, timeout=5)
        response.raise_for_status()
        
        news_data = response.json()
        
        # Get today's date in UTC
        today = timezone.now().date()
        
        # Filter for today's high-impact news
        today_news = []
        for event in news_data:
            impact = event.get('impact', '')
            # Include HIGH and MEDIUM impact news
            if impact in ['HIGH', 'MEDIUM']:
                try:
                    # Parse event time
                    event_time_str = event.get('event_time_utc')
                    if event_time_str:
                        event_time = date_parser.parse(event_time_str)
                        # Convert to local timezone
                        event_time_local = timezone.localtime(event_time)
                        
                        # Check if event is today
                        if event_time_local.date() == today:
                            today_news.append({
                                'time': event_time_local.strftime('%H:%M'),
                                'currency': event.get('currency', ''),
                                'event': event.get('event', ''),
                                'impact': impact,
                                'time_obj': event_time_local,
                            })
                except Exception as e:
                    logger.warning(f"Error parsing news event: {e}")
                    continue
        
        # Sort by time
        today_news.sort(key=lambda x: x['time_obj'])
        
        return today_news
        
    except requests.RequestException as e:
        logger.error(f"Error fetching FX news: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in get_today_high_impact_news: {e}")
        return []


# ============================================
# Authentication Views
# ============================================

def welcome_view(request):
    """Landing page for non-authenticated users"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'auth/welcome.html')


def login_view(request):
    """User login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'เข้าสู่ระบบสำเร็จ')
            return redirect('dashboard')
        else:
            messages.error(request, 'Username หรือ Password ไม่ถูกต้อง')
    
    return render(request, 'auth/login.html')


def register_view(request):
    """User registration with 2-step process"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    step = request.GET.get('step', '1')
    
    if request.method == 'POST':
        if request.POST.get('step') == '2':
            # Step 2: Create user and profile
            username = request.POST.get('username')
            password = request.POST.get('password')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            phone = request.POST.get('phone', '')
            
            # Validation
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username นี้ถูกใช้งานแล้ว')
                return render(request, 'auth/register.html', {'step': 2})
            
            # Create user
            user = User.objects.create_user(username=username, password=password)
            
            # Create profile (without LINE for now)
            # Generate a temporary unique LINE UUID (will be updated when user connects LINE later)
            temp_line_uuid = f'temp_{user.id}_{timezone.now().timestamp()}'
            
            UserProfile.objects.create(
                user=user,
                line_uuid=temp_line_uuid,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone
            )
            
            # Auto login
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'สมัครสมาชิกสำเร็จ')
            return redirect('subscription_packages')
    
    return render(request, 'auth/register.html', {'step': int(step)})


def logout_view(request):
    """User logout"""
    logout(request)
    messages.success(request, 'ออกจากระบบเรียบร้อย')
    return redirect('welcome')


# ============================================
# LINE Login Views
# ============================================

def line_login_view(request):
    """Redirect to LINE OAuth for authentication or connection"""
    if not settings.LINE_CHANNEL_ID:
        messages.warning(request, 'LINE Login ยังไม่ได้ตั้งค่า กรุณาติดต่อผู้ดูแลระบบ')
        # Redirect back to where user came from
        referer = request.META.get('HTTP_REFERER')
        if referer and 'register' in referer:
            return redirect('register')
        elif referer and 'profile' in referer:
            return redirect('profile')
        return redirect('login')
    
    # Store where user came from (for redirect after LINE auth)
    referer = request.META.get('HTTP_REFERER', '')
    if 'register' in referer:
        request.session['line_login_source'] = 'register'
    elif 'profile' in referer:
        request.session['line_login_source'] = 'profile'
    else:
        request.session['line_login_source'] = 'login'
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    request.session['line_login_state'] = state
    
    # Build LINE authorization URL
    params = {
        'response_type': 'code',
        'client_id': settings.LINE_CHANNEL_ID,
        'redirect_uri': settings.LINE_CALLBACK_URL,
        'state': state,
        'scope': 'profile openid email',
    }
    
    line_auth_url = f"https://access.line.me/oauth2/v2.1/authorize?{urllib.parse.urlencode(params)}"
    return redirect(line_auth_url)


def line_callback_view(request):
    """Handle LINE OAuth callback"""
    code = request.GET.get('code')
    state = request.GET.get('state')
    stored_state = request.session.get('line_login_state')
    
    # Verify state for CSRF protection
    if not code or not state or state != stored_state:
        messages.error(request, 'การเข้าสู่ระบบด้วย LINE ล้มเหลว')
        return redirect('login')
    
    try:
        # Exchange code for access token
        token_url = 'https://api.line.me/oauth2/v2.1/token'
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': settings.LINE_CALLBACK_URL,
            'client_id': settings.LINE_CHANNEL_ID,
            'client_secret': settings.LINE_CHANNEL_SECRET,
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_response.raise_for_status()
        token_json = token_response.json()
        access_token = token_json.get('access_token')
        
        if not access_token:
            raise Exception('ไม่สามารถรับ access token จาก LINE')
        
        # Get user profile from LINE
        profile_url = 'https://api.line.me/v2/profile'
        headers = {'Authorization': f'Bearer {access_token}'}
        profile_response = requests.get(profile_url, headers=headers)
        profile_response.raise_for_status()
        profile = profile_response.json()
        
        line_user_id = profile.get('userId')
        display_name = profile.get('displayName', '')
        picture_url = profile.get('pictureUrl', '')
        
        if not line_user_id:
            raise Exception('ไม่สามารถรับข้อมูลผู้ใช้จาก LINE')
        
        # Get source from session
        source = request.session.get('line_login_source', 'login')
        
        # Check if user exists with this LINE ID
        try:
            user_profile = UserProfile.objects.get(line_uuid=line_user_id)
            user = user_profile.user
            
            # Update LINE profile data
            user_profile.line_display_name = display_name
            user_profile.line_picture_url = picture_url
            user_profile.save()
            
            # Login user
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'ยินดีต้อนรับกลับ {display_name}')
            return redirect('dashboard')
            
        except UserProfile.DoesNotExist:
            # Check if this is for LINE connection (user already logged in)
            if source == 'profile' and request.user.is_authenticated:
                # Connect LINE to existing account
                user_profile = request.user.profile
                
                # Check if LINE ID is already used by another account
                if UserProfile.objects.filter(line_uuid=line_user_id).exists():
                    messages.error(request, 'LINE ID นี้ถูกเชื่อมต่อกับบัญชีอื่นแล้ว')
                    return redirect('profile')
                
                # Update user profile with LINE data
                user_profile.line_uuid = line_user_id
                user_profile.line_display_name = display_name
                user_profile.line_picture_url = picture_url
                user_profile.save()
                
                messages.success(request, f'เชื่อมต่อ LINE สำเร็จ! ยินดีต้อนรับ {display_name}')
                return redirect('profile')
            
            # User not found - show error and redirect to login
            messages.error(request, 'ไม่พบบัญชีที่เชื่อมต่อกับ LINE นี้ กรุณาสมัครสมาชิกก่อน')
            return redirect('login')
    
    except Exception as e:
        messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
        
        # Redirect back to source
        source = request.session.get('line_login_source', 'login')
        request.session.pop('line_login_source', None)
        
        if source == 'register':
            return redirect('register?step=2')
        return redirect('login')
    
    finally:
        # Clear state from session
        request.session.pop('line_login_state', None)
        request.session.pop('line_login_source', None)


@login_required
def line_connect_view(request):
    """Alias for line_login_view for clarity"""
    return line_login_view(request)


@login_required
def line_disconnect_view(request):
    """Disconnect LINE from user account"""
    try:
        user_profile = request.user.profile
        
        # Generate new temp LINE UUID
        temp_line_uuid = f'temp_{request.user.id}_{timezone.now().timestamp()}'
        
        # Clear LINE data
        user_profile.line_uuid = temp_line_uuid
        user_profile.line_display_name = ''
        user_profile.line_picture_url = ''
        user_profile.save()
        
        messages.success(request, 'ยกเลิกการเชื่อมต่อ LINE เรียบร้อย')
    except Exception as e:
        messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
    
    return redirect('profile')


# ============================================
# Dashboard Views
# ============================================

@login_required
def dashboard_view(request):
    """Main dashboard showing all trading accounts"""
    accounts = UserTradeAccount.objects.filter(user=request.user, is_active=True).select_related('active_bot')
    
    # Enrich accounts with additional data
    for account in accounts:
        # Get bot status and balance from Redis heartbeat
        redis_data = get_account_data_from_redis(account)
        account.bot_status = redis_data['bot_status']
        account.current_balance = redis_data['balance']
        
        # Count open positions
        account.open_positions_count = TradeTransaction.objects.filter(
            trade_account=account,
            position_status='OPEN',
            is_active=True
        ).count()
        
        # Calculate current PNL from open positions
        open_positions = TradeTransaction.objects.filter(
            trade_account=account,
            position_status='OPEN',
            is_active=True
        )
        account.current_pnl = sum(p.profit_loss for p in open_positions)
        
        # Calculate days until expiry
        if account.subscription_expiry:
            days_remaining = (account.subscription_expiry - timezone.now()).days
            account.days_until_expiry = max(0, days_remaining)
        else:
            account.days_until_expiry = 0
    
    # Fetch today's high-impact news
    today_news = get_today_high_impact_news()
    
    context = {
        'accounts': accounts,
        'today_news': today_news,
    }
    return render(request, 'dashboard/index.html', context)


# ============================================
# Account Views
# ============================================

@login_required
def account_detail_view(request, account_id):
    """Detailed view of a trading account"""
    account = get_object_or_404(UserTradeAccount, id=account_id, user=request.user, is_active=True)
    
    # Get bot status and balance from Redis heartbeat (for real-time balance)
    redis_data = get_account_data_from_redis(account)
    # Use database bot_status (source of truth), Redis balance for real-time updates
    # account.bot_status is already loaded from database
    account.current_balance = redis_data['balance']  # Only update balance from Redis
    
    # Get open positions
    open_positions = TradeTransaction.objects.filter(
        trade_account=account,
        position_status='OPEN',
        is_active=True
    ).select_related('trade_account', 'bot_strategy').order_by('-opened_at')
    
    # Get closed positions (last 50)
    closed_positions = TradeTransaction.objects.filter(
        trade_account=account,
        position_status='CLOSED',
        is_active=True
    ).select_related('trade_account', 'bot_strategy').order_by('-closed_at')[:50]
    
    # Calculate statistics
    all_closed = TradeTransaction.objects.filter(
        trade_account=account,
        position_status='CLOSED',
        is_active=True
    )
    
    account.total_trades = all_closed.count()
    account.total_pnl = sum(t.profit_loss for t in all_closed)
    
    winning_trades = all_closed.filter(profit_loss__gt=0).count()
    account.win_rate = (winning_trades / account.total_trades * 100) if account.total_trades > 0 else 0
    
    # Get available bots for selection/change
    available_bots = []
    if account.subscription_package:
        available_bots = BotStrategy.objects.filter(
            status='ACTIVE',
            allowed_packages=account.subscription_package
        )
    else:
        # No subscription, show all active bots
        available_bots = BotStrategy.objects.filter(status='ACTIVE')
    
    # Equity curve data (last 30 days)
    equity_data = []
    for i in range(30, 0, -1):
        date = timezone.now() - timedelta(days=i)
        # This is simplified - in real implementation, calculate actual balance at each date
        equity_data.append([int(date.timestamp() * 1000), float(account.current_balance)])
    
    context = {
        'account': account,
        'open_positions': open_positions,
        'closed_positions': closed_positions,
        'equity_data': equity_data,
        'available_bots': available_bots
    }
    return render(request, 'accounts/detail.html', context)


@login_required
def account_update_bot_config(request, account_id):
    """Update bot configuration for an account"""
    if request.method != 'POST':
        return redirect('account_detail', account_id=account_id)
    
    account = get_object_or_404(UserTradeAccount, id=account_id, user=request.user, is_active=True)
    
    if not account.active_bot:
        messages.error(request, 'ไม่มี Bot ที่กำลังใช้งาน')
        return redirect('account_detail', account_id=account_id)
    
    # Get package limits
    package = account.subscription_package
    max_symbols = package.max_symbols if package else 0
    max_lot_size = package.max_lot_size if package else None
    min_lot_size = package.min_lot_size if package else Decimal('0.01')
    
    # Get enabled symbols
    enabled_symbols = request.POST.getlist('enabled_symbols')
    if not enabled_symbols:
        messages.error(request, 'กรุณาเลือกอย่างน้อย 1 Symbol')
        return redirect('account_detail', account_id=account_id)
    
    # Check symbol limit (0 = unlimited)
    if max_symbols > 0 and len(enabled_symbols) > max_symbols:
        messages.error(request, f'แพคเกจของคุณจำกัดการเลือกได้สูงสุด {max_symbols} คู่เงินเท่านั้น')
        return redirect('account_detail', account_id=account_id)
    
    # Validate symbols against bot's allowed symbols
    for symbol in enabled_symbols:
        if symbol not in account.active_bot.allowed_symbols:
            messages.error(request, f'Symbol {symbol} ไม่ได้รับอนุญาตจาก Bot นี้')
            return redirect('account_detail', account_id=account_id)
    
    # Get lot size
    try:
        lot_size = Decimal(str(request.POST.get('lot_size', '0.01')))
        if lot_size <= 0:
            raise ValueError('Lot size must be greater than 0')
    except (ValueError, TypeError, InvalidOperation):
        messages.error(request, 'Lot Size ไม่ถูกต้อง')
        return redirect('account_detail', account_id=account_id)
    
    # Check lot size limits
    if lot_size < min_lot_size:
        messages.error(request, f'Lot Size ต้องไม่น้อยกว่า {min_lot_size}')
        return redirect('account_detail', account_id=account_id)
    
    if max_lot_size and lot_size > max_lot_size:
        messages.error(request, f'แพคเกจของคุณจำกัด Lot Size สูงสุดที่ {max_lot_size} เท่านั้น')
        return redirect('account_detail', account_id=account_id)
    
    # Get auto pause on news setting (only if package allows)
    auto_pause_on_news = False
    if package and package.allow_news_filter:
        auto_pause_on_news = request.POST.get('auto_pause_on_news') == 'on'
    
    # Get drawdown protection settings (only if package allows)
    daily_dd_limit = None
    max_dd_limit = None
    if package and package.allow_dd_protection:
        try:
            daily_dd_value = request.POST.get('daily_dd_limit', '').strip()
            if daily_dd_value:
                daily_dd_limit = float(daily_dd_value)
                if daily_dd_limit < 0 or daily_dd_limit > 100:
                    messages.error(request, 'Daily Drawdown Limit ต้องอยู่ระหว่าง 0-100%')
                    return redirect('account_detail', account_id=account_id)
                # If it's 0, treat as disabled
                if daily_dd_limit == 0:
                    daily_dd_limit = None
        except (ValueError, TypeError):
            messages.error(request, 'Daily Drawdown Limit ไม่ถูกต้อง')
            return redirect('account_detail', account_id=account_id)
        
        try:
            max_dd_value = request.POST.get('max_dd_limit', '').strip()
            if max_dd_value:
                max_dd_limit = float(max_dd_value)
                if max_dd_limit < 0 or max_dd_limit > 100:
                    messages.error(request, 'Max Account Drawdown ต้องอยู่ระหว่าง 0-100%')
                    return redirect('account_detail', account_id=account_id)
                # If it's 0, treat as disabled
                if max_dd_limit == 0:
                    max_dd_limit = None
        except (ValueError, TypeError):
            messages.error(request, 'Max Account Drawdown ไม่ถูกต้อง')
            return redirect('account_detail', account_id=account_id)
    
    # Get dynamic position sizing settings (only if package allows)
    dynamic_position_sizing_enabled = False
    risk_percentage_per_trade = None
    if package and package.allow_dynamic_position_sizing:
        dynamic_position_sizing_enabled = request.POST.get('dynamic_position_sizing_enabled') == 'on'
        
        if dynamic_position_sizing_enabled:
            try:
                risk_value = request.POST.get('risk_percentage_per_trade', '0.5').strip()
                if risk_value:
                    risk_percentage_per_trade = float(risk_value)
                    if risk_percentage_per_trade < 0.1 or risk_percentage_per_trade > 5:
                        messages.error(request, 'Risk Percentage ต้องอยู่ระหว่าง 0.1-5%')
                        return redirect('account_detail', account_id=account_id)
            except (ValueError, TypeError):
                messages.error(request, 'Risk Percentage ไม่ถูกต้อง')
                return redirect('account_detail', account_id=account_id)
    
    # Update trade_config
    trade_config = account.trade_config or {}
    trade_config['enabled_symbols'] = enabled_symbols
    trade_config['lot_size'] = float(lot_size)
    trade_config['auto_pause_on_news'] = auto_pause_on_news
    trade_config['daily_dd_limit'] = daily_dd_limit
    trade_config['max_dd_limit'] = max_dd_limit
    trade_config['dynamic_position_sizing_enabled'] = dynamic_position_sizing_enabled
    trade_config['risk_percentage_per_trade'] = risk_percentage_per_trade
    
    # Ensure enabled_strategies exists and is correct
    if account.active_bot:
        trade_config['enabled_strategies'] = [account.active_bot.id]
    elif 'enabled_strategies' not in trade_config:
        trade_config['enabled_strategies'] = []
    
    account.trade_config = trade_config
    account.save()
    
    # Update server heartbeat in Redis to notify bot
    update_server_heartbeat_in_redis(account)
    
    messages.success(request, 'อัพเดทการตั้งค่า Bot เรียบร้อยแล้ว')
    return redirect('account_detail', account_id=account_id)


@login_required
def account_bot_pause_view(request, account_id):
    """Pause bot for an account"""
    if request.method != 'POST':
        return redirect('account_detail', account_id=account_id)
    
    account = get_object_or_404(UserTradeAccount, id=account_id, user=request.user)
    
    if account.bot_status == 'PAUSED':
        messages.warning(request, 'Bot อยู่ในสถานะ Pause อยู่แล้ว')
    else:
        account.bot_status = 'PAUSED'
        account.save(update_fields=['bot_status', 'updated_at'])
        
        # Update server heartbeat in Redis
        update_server_heartbeat_in_redis(account)
        
        messages.success(request, f'Bot ถูก Pause เรียบร้อยแล้ว')
    
    return redirect('account_detail', account_id=account_id)


@login_required
def account_bot_resume_view(request, account_id):
    """Resume bot for an account"""
    if request.method != 'POST':
        return redirect('account_detail', account_id=account_id)
    
    account = get_object_or_404(UserTradeAccount, id=account_id, user=request.user)
    
    if not account.active_bot:
        messages.error(request, 'ไม่มี Bot ที่เชื่อมต่ออยู่ กรุณาเลือก Bot ก่อน')
    elif account.bot_status == 'ACTIVE':
        messages.warning(request, 'Bot กำลังทำงานอยู่แล้ว')
    else:
        account.bot_status = 'ACTIVE'
        account.save(update_fields=['bot_status', 'updated_at'])
        
        # Update server heartbeat in Redis
        update_server_heartbeat_in_redis(account)
        
        messages.success(request, f'Bot เริ่มทำงานอีกครั้งเรียบร้อยแล้ว')
    
    return redirect('account_detail', account_id=account_id)


@login_required
def accounts_list_view(request):
    """List all accounts - redirects to dashboard"""
    return redirect('dashboard')


# ============================================
# Subscription Views
# ============================================

@login_required
def subscription_packages_view(request):
    """Display available subscription packages"""
    packages = SubscriptionPackage.objects.filter(is_active=True).order_by('price')
    
    # Check if this is for renewal
    renew_account_id = request.GET.get('renew_account')
    renew_account = None
    if renew_account_id:
        try:
            renew_account = UserTradeAccount.objects.get(
                id=renew_account_id, 
                user=request.user, 
                is_active=True
            )
        except UserTradeAccount.DoesNotExist:
            messages.error(request, 'ไม่พบบัญชีที่ต้องการต่ออายุ')
            return redirect('profile')
    
    # Add features list to each package
    for package in packages:
        if isinstance(package.features, dict):
            package.features_list = package.features.get('items', [])
        else:
            package.features_list = [
                'Real-time monitoring',
                'LINE notifications',
                'Trade history',
                'Bot control panel'
            ]
        # Mark popular package (optional)
        package.is_popular = False
    
    context = {
        'packages': packages,
        'renew_account': renew_account
    }
    return render(request, 'subscription/packages.html', context)


@login_required
def payment_view(request):
    """Payment page with QR code"""
    package_id = request.GET.get('package')
    renew_account_id = request.GET.get('renew_account')
    
    if not package_id:
        messages.error(request, 'กรุณาเลือกแพ็คเกจ')
        return redirect('subscription_packages')
    
    package = get_object_or_404(SubscriptionPackage, id=package_id, is_active=True)
    
    # Check if this is for renewal
    renew_account = None
    if renew_account_id:
        try:
            renew_account = UserTradeAccount.objects.get(
                id=renew_account_id, 
                user=request.user, 
                is_active=True
            )
        except UserTradeAccount.DoesNotExist:
            messages.error(request, 'ไม่พบบัญชีที่ต้องการต่ออายุ')
            return redirect('profile')
    
    context = {
        'package': package,
        'renew_account': renew_account
    }
    return render(request, 'subscription/payment.html', context)


@login_required
def payment_submit_view(request):
    """Handle payment slip upload"""
    if request.method == 'POST':
        package_id = request.POST.get('package_id')
        renew_account_id = request.POST.get('renew_account_id')
        account_name = request.POST.get('account_name')
        mt5_account_id = request.POST.get('mt5_account_id')
        mt5_password = request.POST.get('mt5_password')
        mt5_server = request.POST.get('mt5_server')
        payment_slip = request.FILES.get('payment_slip')
        
        package = get_object_or_404(SubscriptionPackage, id=package_id)
        
        # Check if this is a renewal
        is_renewal = False
        trade_account = None
        
        if renew_account_id:
            try:
                trade_account = UserTradeAccount.objects.get(
                    id=renew_account_id,
                    user=request.user,
                    is_active=True
                )
                is_renewal = True
            except UserTradeAccount.DoesNotExist:
                messages.error(request, 'ไม่พบบัญชีที่ต้องการต่ออายุ')
                return redirect('profile')
        
        # Validate required fields based on renewal or new account
        if is_renewal:
            # For renewal, only payment slip is required
            if not payment_slip:
                messages.error(request, 'กรุณาอัพโหลดสลิปโอนเงิน')
                return redirect('payment')
            
            # Update the trade account subscription details (will be activated after payment confirmation)
            # Calculate new expiry date from current expiry or now (whichever is later)
            current_expiry = trade_account.subscription_expiry
            if current_expiry and current_expiry > timezone.now():
                # Extend from current expiry
                new_expiry = current_expiry + timedelta(days=package.duration_days)
            else:
                # Start fresh from now
                new_expiry = timezone.now() + timedelta(days=package.duration_days)
            
            # Store the new expiry in a temporary field or track it through payment
            # We'll update it when payment is confirmed
            # For now, keep the account in current status
            
        else:
            # For new account, all fields are required
            if not all([account_name, mt5_account_id, mt5_password, mt5_server, payment_slip]):
                messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')
                return redirect('payment')
            
            # Create trade account with MT5 credentials
            trade_account = UserTradeAccount.objects.create(
                user=request.user,
                account_name=account_name,
                mt5_account_id=mt5_account_id,
                mt5_password=mt5_password,  # TODO: Should encrypt this in production
                broker_name='Pending Setup',
                mt5_server=mt5_server,
                subscription_package=package,
                subscription_start=timezone.now(),
                subscription_expiry=timezone.now() + timedelta(days=package.duration_days),
                subscription_status='PENDING',
                bot_status='PAUSED'
            )
        
        # Create subscription payment record with trade_account
        payment = SubscriptionPayment.objects.create(
            user=request.user,
            trade_account=trade_account,
            subscription_package=package,
            payment_amount=package.price,
            payment_status='PENDING',
            payment_method='Bank Transfer',
            payment_slip=payment_slip,
            payment_date=timezone.now(),
            # Store renewal info in admin_notes for reference
            admin_notes=f'Renewal for account: {trade_account.account_name}' if is_renewal else ''
        )
        
        if is_renewal:
            messages.success(request, f'ส่งหลักฐานการต่ออายุเรียบร้อย รอการตรวจสอบจากทีมงาน')
        else:
            messages.success(request, 'ส่งหลักฐานการชำระเงินเรียบร้อย')
        
        return redirect('payment_pending', payment_id=payment.id)
    
    return redirect('subscription_packages')


@login_required
def payment_pending_view(request, payment_id):
    """Payment pending confirmation page"""
    payment = get_object_or_404(SubscriptionPayment, id=payment_id, user=request.user)
    
    context = {
        'payment': payment,
        'package': payment.subscription_package
    }
    return render(request, 'subscription/payment_pending.html', context)


@login_required
def payment_reupload_view(request, payment_id):
    """Allow user to re-upload payment slip if payment was marked as FAILED"""
    payment = get_object_or_404(SubscriptionPayment, id=payment_id, user=request.user)
    
    # Only allow re-upload if payment status is FAILED
    if payment.payment_status != PaymentStatus.FAILED:
        messages.error(request, 'ไม่สามารถอัพโหลดสลิปใหม่ได้ สถานะการชำระเงินไม่ถูกต้อง')
        return redirect('dashboard')
    
    if request.method == 'POST':
        payment_slip = request.FILES.get('payment_slip')
        
        if not payment_slip:
            messages.error(request, 'กรุณาเลือกไฟล์สลิปโอนเงิน')
            return redirect('payment_reupload', payment_id=payment.id)
        
        # Update payment with new slip
        payment.payment_slip = payment_slip
        payment.payment_status = PaymentStatus.PENDING  # Reset to PENDING
        payment.payment_date = timezone.now()  # Update payment date
        payment.admin_notes = ''  # Clear old admin notes
        payment.save()
        
        messages.success(request, 'อัพโหลดสลิปใหม่สำเร็จ กรุณารอการตรวจสอบจากทีมงาน')
        return redirect('payment_pending', payment_id=payment.id)
    
    context = {
        'payment': payment,
        'package': payment.subscription_package
    }
    return render(request, 'subscription/payment_reupload.html', context)


# ============================================
# Profile Views
# ============================================

@login_required
def profile_view(request):
    """User profile and subscription management"""
    # Get all subscriptions
    trade_accounts = UserTradeAccount.objects.filter(user=request.user, is_active=True)
    
    subscriptions = []
    for account in trade_accounts:
        days_remaining = (account.subscription_expiry - timezone.now()).days if account.subscription_expiry else 0
        
        # Find related payment (latest one)
        payment = SubscriptionPayment.objects.filter(
            user=request.user,
            trade_account=account
        ).order_by('-created_at').first()
        
        # Check if there's a pending renewal payment
        has_pending_renewal = False
        if payment and payment.payment_status == 'PENDING' and payment.admin_notes and 'Renewal' in payment.admin_notes:
            has_pending_renewal = True
        
        subscriptions.append({
            'account': account,
            'package': account.subscription_package,
            'status': account.subscription_status,
            'get_status_display': account.get_subscription_status_display(),
            'start_date': account.subscription_start,
            'expiry_date': account.subscription_expiry,
            'days_remaining': max(0, days_remaining),
            'payment_id': payment.id if payment else None,
            'payment_status': payment.payment_status if payment else None,
            'payment_admin_notes': payment.admin_notes if payment else None,
            'has_pending_renewal': has_pending_renewal
        })
    
    # Calculate totals
    total_accounts = trade_accounts.count()
    active_accounts = trade_accounts.filter(subscription_status='ACTIVE').count()
    
    context = {
        'subscriptions': subscriptions,
        'total_accounts': total_accounts,
        'active_accounts': active_accounts
    }
    return render(request, 'profile/index.html', context)


# ============================================
# Trade History Views
# ============================================

@login_required
def trades_history_view(request):
    """Complete trade history with filters"""
    # Get filter parameters
    account_id = request.GET.get('account')
    bot_id = request.GET.get('bot')
    
    # Base query - all closed trades for user's accounts
    user_accounts = UserTradeAccount.objects.filter(user=request.user, is_active=True)
    trades = TradeTransaction.objects.filter(
        trade_account__in=user_accounts,
        position_status='CLOSED',
        is_active=True
    ).select_related('trade_account', 'bot_strategy')
    
    # Apply filters
    if account_id:
        trades = trades.filter(trade_account_id=account_id)
    
    if bot_id:
        trades = trades.filter(bot_strategy_id=bot_id)
    
    # Calculate statistics before slicing
    total_trades = trades.count()
    winning_trades = trades.filter(profit_loss__gt=0).count()
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    total_pnl = sum(t.profit_loss for t in trades)
    
    # Apply ordering and limit
    trades = trades.order_by('-closed_at')[:100]
    
    # Add duration to each trade
    for trade in trades:
        if trade.closed_at and trade.opened_at:
            duration = trade.closed_at - trade.opened_at
            hours = int(duration.total_seconds() / 3600)
            minutes = int((duration.total_seconds() % 3600) / 60)
            trade.duration = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        else:
            trade.duration = "-"
    
    # Get all bots for filter
    bots = BotStrategy.objects.filter(is_active=True).order_by('name')
    
    context = {
        'trades': trades,
        'accounts': user_accounts,
        'bots': bots,
        'selected_account_id': account_id,
        'selected_bot_id': bot_id,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'has_more': total_trades > 100
    }
    return render(request, 'trades/history.html', context)


# ============================================
# Bot Strategy Views
# ============================================

def bots_list_view(request):
    """List all available bot strategies"""
    # Get all active bot strategies with prefetch
    bots = BotStrategy.objects.filter(
        is_active=True,
        # status='ACTIVE'
    ).prefetch_related('allowed_packages').order_by('-created_at')
    
    # Add latest backtest result to each bot
    for bot in bots:
        bot.latest_backtest = bot.get_latest_backtest()
    
    context = {
        'bots': bots
    }
    return render(request, 'bots/list.html', context)


def bot_detail_view(request, bot_id):
    """Detailed view of a specific bot strategy"""
    bot = get_object_or_404(
        BotStrategy.objects.prefetch_related('allowed_packages'),
        id=bot_id,
        is_active=True
    )
    
    # Get latest backtest result
    latest_backtest = bot.get_latest_backtest()
    
    # Get user's accounts if logged in (to check compatibility)
    user_accounts = None
    if request.user.is_authenticated:
        user_accounts = UserTradeAccount.objects.filter(
            user=request.user,
            is_active=True,
            subscription_status='ACTIVE'
        )
    
    context = {
        'bot': bot,
        'latest_backtest': latest_backtest,
        'user_accounts': user_accounts,
        'allowed_packages': bot.allowed_packages.all()
    }
    return render(request, 'bots/detail.html', context)


@login_required
def account_bot_activate_view(request, account_id):
    """Activate a bot for a specific account"""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return redirect('account_detail', account_id=account_id)
    
    # Get account and verify ownership
    account = get_object_or_404(
        UserTradeAccount,
        id=account_id,
        user=request.user,
        is_active=True
    )
    
    # Get bot_id from POST
    bot_id = request.POST.get('bot_id')
    if not bot_id:
        messages.error(request, 'กรุณาเลือก Bot')
        return redirect('account_detail', account_id=account_id)
    
    try:
        # Get bot strategy
        bot = BotStrategy.objects.get(id=bot_id, is_active=True, status='ACTIVE')
    except BotStrategy.DoesNotExist:
        messages.error(request, 'ไม่พบ Bot ที่เลือก')
        return redirect('account_detail', account_id=account_id)
    
    # Validate subscription package (only if bot has package restrictions)
    if bot.allowed_packages.exists():
        if not account.subscription_package:
            messages.error(request, 'บัญชีนี้ยังไม่มี Subscription Package')
            return redirect('account_detail', account_id=account_id)
        
        if not bot.allowed_packages.filter(id=account.subscription_package.id).exists():
            messages.error(request, f'แพ็คเกจของคุณไม่รองรับ Bot นี้')
            return redirect('account_detail', account_id=account_id)
    
    # Validate subscription is active
    if account.subscription_status != 'ACTIVE':
        messages.error(request, 'บัญชีนี้ไม่ได้เปิดใช้งาน Subscription')
        return redirect('account_detail', account_id=account_id)
    
    # Check if subscription has expired
    if account.subscription_expiry and account.subscription_expiry < timezone.now():
        messages.error(request, 'Subscription ของคุณหมดอายุแล้ว')
        return redirect('account_detail', account_id=account_id)
    
    # Activate bot
    old_bot = account.active_bot
    account.active_bot = bot
    account.bot_activated_at = timezone.now()
    
    # Reset trade_config when changing bot or first time activation
    if (old_bot and old_bot.id != bot.id) or not old_bot:
        # Reset all bot config to defaults
        min_lot = account.subscription_package.min_lot_size if account.subscription_package else Decimal('0.01')
        
        account.trade_config = {
            'enabled_symbols': bot.allowed_symbols.copy(),
            'enabled_strategies': [bot.id],
            'lot_size': float(min_lot),
            'auto_pause_on_news': False,
            'daily_dd_limit': None,
            'max_dd_limit': None,
            'dynamic_position_sizing_enabled': False,
            'risk_percentage_per_trade': 0.5
        }
        
        if old_bot and old_bot.id != bot.id:
            messages.info(request, 'Bot config ถูก reset ทั้งหมดตามการตั้งค่าเริ่มต้นของ Bot ใหม่')
    else:
        # Update enabled_strategies even if bot is the same (to ensure consistency)
        if 'enabled_strategies' not in account.trade_config or account.trade_config.get('enabled_strategies') != [bot.id]:
            account.trade_config['enabled_strategies'] = [bot.id]
    
    account.save(update_fields=['active_bot', 'bot_activated_at', 'trade_config'])
    
    # Update server heartbeat in Redis to notify bot
    update_server_heartbeat_in_redis(account)
    
    messages.success(request, f'เปิดใช้งาน Bot "{bot.name}" สำเร็จ')
    return redirect('account_detail', account_id=account_id)


@login_required
def account_bot_deactivate_view(request, account_id):
    """Deactivate bot for a specific account"""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return redirect('account_detail', account_id=account_id)
    
    # Get account and verify ownership
    account = get_object_or_404(
        UserTradeAccount,
        id=account_id,
        user=request.user,
        is_active=True
    )
    
    # Deactivate bot
    if account.active_bot:
        bot_name = account.active_bot.name
        account.active_bot = None
        account.bot_activated_at = None
        
        # Clear enabled_strategies from trade_config
        if 'enabled_strategies' in account.trade_config:
            account.trade_config['enabled_strategies'] = []
        
        account.save(update_fields=['active_bot', 'bot_activated_at', 'trade_config'])
        
        # Update server heartbeat in Redis to notify bot
        update_server_heartbeat_in_redis(account)
        
        messages.success(request, f'ปิดใช้งาน Bot "{bot_name}" สำเร็จ')
    else:
        messages.info(request, 'ไม่มี Bot ที่เปิดใช้งานอยู่')
    
    return redirect('account_detail', account_id=account_id)


# ============================================
# Admin Dashboard View
# ============================================

@login_required
def admin_dashboard_view(request):
    """
    Admin Dashboard for monitoring all trade accounts.
    Only accessible by superusers/staff.
    """
    # Check if user is admin
    if not request.user.is_staff:
        messages.error(request, 'คุณไม่มีสิทธิ์เข้าถึงหน้านี้')
        return redirect('dashboard')
    
    # Get all active trade accounts
    accounts = UserTradeAccount.objects.filter(
        is_active=True
    ).select_related(
        'user',
        'user__profile',
        'subscription_package',
        'active_bot'
    ).order_by('-subscription_status', '-subscription_expiry')
    
    # Prepare account data with Redis info
    accounts_data = []
    for account in accounts:
        # Get Redis data (bot status and current balance)
        redis_data = get_account_data_from_redis(account)
        
        # Calculate days until expiry
        days_until_expiry = None
        if account.subscription_expiry:
            delta = account.subscription_expiry - timezone.now()
            days_until_expiry = delta.days
        
        # Check if bot is down (no heartbeat)
        bot_status_display = redis_data['bot_status']
        if redis_data['bot_status'] == 'DOWN':
            bot_status_class = 'danger'
        elif redis_data['bot_status'] == 'PAUSED':
            bot_status_class = 'warning'
        else:
            bot_status_class = 'success'
        
        # Subscription status class
        if account.subscription_status == 'ACTIVE':
            sub_status_class = 'success'
        elif account.subscription_status == 'EXPIRED':
            sub_status_class = 'danger'
        else:
            sub_status_class = 'warning'
        
        # Count open positions
        open_positions_count = TradeTransaction.objects.filter(
            trade_account=account,
            position_status='OPEN',
            is_active=True
        ).count()
        
        accounts_data.append({
            'account': account,
            'bot_status': bot_status_display,
            'bot_status_class': bot_status_class,
            'current_balance': redis_data['balance'],
            'days_until_expiry': days_until_expiry,
            'sub_status_class': sub_status_class,
            'user_full_name': f"{account.user.profile.first_name} {account.user.profile.last_name}" if hasattr(account.user, 'profile') else account.user.username,
            'open_positions_count': open_positions_count,
        })
    
    # Statistics
    total_accounts = accounts.count()
    active_subscriptions = accounts.filter(subscription_status='ACTIVE').count()
    live_bots = sum(1 for data in accounts_data if data['bot_status'] == 'ACTIVE')
    
    # Calculate total revenue from completed payments
    from django.db.models import Sum
    total_revenue = SubscriptionPayment.objects.filter(
        payment_status='COMPLETED'
    ).aggregate(total=Sum('payment_amount'))['total'] or 0
    
    # Fetch today's high-impact news
    today_news = get_today_high_impact_news()
    
    context = {
        'accounts_data': accounts_data,
        'total_accounts': total_accounts,
        'active_subscriptions': active_subscriptions,
        'live_bots': live_bots,
        'total_revenue': total_revenue,
        'today_news': today_news,
        'now': timezone.now(),
    }
    
    return render(request, 'admin/dashboard.html', context)
