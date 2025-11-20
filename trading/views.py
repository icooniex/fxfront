from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import requests
import urllib.parse
import secrets
from .models import (
    UserProfile,
    SubscriptionPackage,
    UserTradeAccount,
    TradeTransaction,
    SubscriptionPayment
)


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
    accounts = UserTradeAccount.objects.filter(user=request.user, is_active=True)
    
    # Enrich accounts with additional data
    for account in accounts:
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
    
    context = {
        'accounts': accounts
    }
    return render(request, 'dashboard/index.html', context)


# ============================================
# Account Views
# ============================================

@login_required
def account_detail_view(request, account_id):
    """Detailed view of a trading account"""
    account = get_object_or_404(UserTradeAccount, id=account_id, user=request.user, is_active=True)
    
    # Get open positions
    open_positions = TradeTransaction.objects.filter(
        trade_account=account,
        position_status='OPEN',
        is_active=True
    ).order_by('-opened_at')
    
    # Get closed positions (last 50)
    closed_positions = TradeTransaction.objects.filter(
        trade_account=account,
        position_status='CLOSED',
        is_active=True
    ).order_by('-closed_at')[:50]
    
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
        'equity_data': equity_data
    }
    return render(request, 'accounts/detail.html', context)


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
        'packages': packages
    }
    return render(request, 'subscription/packages.html', context)


@login_required
def payment_view(request):
    """Payment page with QR code"""
    package_id = request.GET.get('package')
    
    if not package_id:
        messages.error(request, 'กรุณาเลือกแพ็คเกจ')
        return redirect('subscription_packages')
    
    package = get_object_or_404(SubscriptionPackage, id=package_id, is_active=True)
    
    context = {
        'package': package
    }
    return render(request, 'subscription/payment.html', context)


@login_required
def payment_submit_view(request):
    """Handle payment slip upload"""
    if request.method == 'POST':
        package_id = request.POST.get('package_id')
        account_name = request.POST.get('account_name')
        payment_slip = request.FILES.get('payment_slip')
        
        package = get_object_or_404(SubscriptionPackage, id=package_id)
        
        # Create placeholder trade account first
        trade_account = UserTradeAccount.objects.create(
            user=request.user,
            account_name=account_name,
            mt5_account_id='PENDING',
            broker_name='Pending Setup',
            mt5_server='Pending',
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
            payment_date=timezone.now()
        )
        
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
        subscriptions.append({
            'account': account,
            'package': account.subscription_package,
            'status': account.subscription_status,
            'start_date': account.subscription_start,
            'expiry_date': account.subscription_expiry,
            'days_remaining': max(0, days_remaining)
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
    status = request.GET.get('status')
    
    # Base query - all closed trades for user's accounts
    user_accounts = UserTradeAccount.objects.filter(user=request.user, is_active=True)
    trades = TradeTransaction.objects.filter(
        trade_account__in=user_accounts,
        position_status='CLOSED',
        is_active=True
    )
    
    # Apply filters
    if account_id:
        trades = trades.filter(trade_account_id=account_id)
    
    if status == 'profit':
        trades = trades.filter(profit_loss__gt=0)
    elif status == 'loss':
        trades = trades.filter(profit_loss__lt=0)
    
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
    
    context = {
        'trades': trades,
        'accounts': user_accounts,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'has_more': total_trades > 100
    }
    return render(request, 'trades/history.html', context)
